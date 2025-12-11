"""
Invoice Processing Agent using Claude with Tool Use
Extracts invoice data, validates, and flags anomalies
Supports PDF files by converting them to images
"""

import anthropic
import base64
import json
import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import mimetypes
import os
from dotenv import load_dotenv

try:
    from pdf2image import convert_from_path
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    import docx
    DOCX_SUPPORT = True
except ImportError:
    DOCX_SUPPORT = False

# Load environment variables from .env file
load_dotenv()

# Initialize Anthropic client - explicitly use API key from environment
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please set it in your .env file.")
client = anthropic.Anthropic(api_key=api_key)

# Model configuration - can be overridden via environment variable
DEFAULT_MODEL = os.getenv('INVOICE_MODEL', 'claude-opus-4-1-20250805')
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2048'))

from database import SessionLocal
from models import Vendor, PurchaseOrder, Invoice, InvoiceLine, GoodsReceipt
from sqlalchemy import or_


def validate_vendor(vendor_name: str) -> dict:
    """Check if vendor exists in database"""
    if isinstance(vendor_name, dict):
         vendor_name = vendor_name.get("value") or vendor_name.get("name") or str(vendor_name)
         
    vendor_clean = str(vendor_name).strip()
    db = SessionLocal()
    try:
        # 1. Exact Name Match (Case Insensitive)
        vendor = db.query(Vendor).filter(Vendor.name.ilike(vendor_clean)).first()
        
        if vendor:
            return {
                "valid": True,
                "vendor_id": vendor.vendor_id,
                "category": vendor.category,
                "message": f"Vendor '{vendor_name}' found in database"
            }
            
        # 2. Fuzzy / Containment Search
        # Check if input contains db name OR db name contains input
        all_vendors = db.query(Vendor).all()
        for v in all_vendors:
            if v.name.lower() in vendor_clean.lower() or vendor_clean.lower() in v.name.lower():
                 return {
                    "valid": True,
                    "vendor_id": v.vendor_id,
                    "category": v.category,
                    "message": f"Vendor '{vendor_name}' matched to '{v.name}' in database (fuzzy match)"
                }
        
        return {
            "valid": False,
            "vendor_id": None,
            "category": None,
            "message": f"Vendor '{vendor_name}' NOT found in database"
        }
    finally:
        db.close()


def perform_3_way_match(po_number: str, vendor_name: str, invoice_amount: float) -> dict:
    """
    Perform 2-way and 3-way matching validation.
    Returns validation status and match details.
    """
    
    if not po_number:
        return {
            "valid": False,
            "message": "No PO number provided",
            "po_found": False
        }
    
    po_clean = po_number.strip()
    db = SessionLocal()
    
    try:
        po_obj = db.query(PurchaseOrder).filter(PurchaseOrder.po_number.ilike(po_clean)).first()
        
        if not po_obj:
            return {
                "valid": False,
                "message": f"PO '{po_number}' not found in database",
                "po_found": False
            }
        
        # 1. Vendor Match
        po_vendor = po_obj.vendor
        vendor_match = False
        if po_vendor:
            v_name_db = po_vendor.name.lower()
            v_name_inv = vendor_name.lower()
            if v_name_db in v_name_inv or v_name_inv in v_name_db:
                vendor_match = True
        
        if not vendor_match:
             return {
                "valid": False,
                "message": f"Vendor mismatch: Invoice from '{vendor_name}' but PO is for '{po_vendor.name if po_vendor else 'Unknown'}'",
                "po_found": True,
                "match_type": "failed_vendor"
            }
        
        # 2. Amount Validation (2-Way)
        expected = po_obj.expected_amount
        tolerance = po_obj.tolerance
        tolerance_amount = expected * tolerance
        
        amount_check = True
        if invoice_amount < expected - tolerance_amount or invoice_amount > expected + tolerance_amount:
            amount_check = False
            
        # 3. Goods Receipt Validation (3-Way)
        receipts = po_obj.receipts
        total_received = sum(r.amount for r in receipts)
        
        has_receipts = len(receipts) > 0
        receipt_match = False
        
        # Logic: Invoice should not exceed Received Amount + Tolerance
        # Or if no receipts, flag it.
        if has_receipts:
            if invoice_amount <= total_received * (1.0 + tolerance):
                receipt_match = True
            else:
                receipt_match = False
        
        # Construct Result
        result = {
            "po_found": True,
            "vendor_match": True,
            "expected_po_amount": expected,
            "total_goods_received": total_received,
            "has_receipts": has_receipts,
            "2_way_match": amount_check,
            "3_way_match": receipt_match if has_receipts else "skipped"
        }
        
        if not amount_check:
            result["valid"] = False
            result["message"] = f"2-Way Match Candidate Failed: Invoice ${invoice_amount} vs PO ${expected}"
            result["match_type"] = "2_way_failure"
            
        elif has_receipts and not receipt_match:
            result["valid"] = False
            result["message"] = f"3-Way Match Failed: Invoice ${invoice_amount} exceeds Goods Received ${total_received}"
            result["match_type"] = "3_way_failure"
            
        elif not has_receipts:
             # Weak Validation if no receipts yet
            result["valid"] = True
            result["message"] = f"2-Way Match Passed (Note: No Goods Receipts found for 3-way check)"
            result["match_type"] = "2_way_success"
            
        else:
            result["valid"] = True
            result["message"] = f"3-Way Match Successful! (Invoice matches PO and Goods Receipts)"
            result["match_type"] = "3_way_success"
            
        return result
            
    finally:
        db.close()


def flag_anomaly(anomaly_type: str, description: str, severity: str = "medium") -> dict:
    """Record an anomaly for review"""
    return {
        "flagged": True,
        "anomaly_type": anomaly_type,
        "description": description,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "message": f"Anomaly flagged: {anomaly_type} ({severity})"
    }


def calculate_optimal_payment(terms: str, invoice_date_str: str, amount: float) -> dict:
    """
    Calculate due date and optimal payment date based on terms.
    """
    try:
        inv_date = datetime.strptime(invoice_date_str, "%Y-%m-%d")
    except:
        return {
            "error": "Invalid date format. Use YYYY-MM-DD"
        }
    
    terms = terms.lower().strip()
    result = {
        "payment_terms": terms,
        "invoice_date": invoice_date_str,
        "due_date": None,
        "discount_date": None,
        "optimal_payment_date": None,
        "potential_savings": 0.0,
        "reasoning": "Standard Net Terms"
    }
    
    # 1. Parse "2/10 Net 30" style
    # Regex for "X/Y Net Z" or "X/Y, Net Z"
    match = re.search(r'(\d+(?:\.\d+)?)%?\/(\d+)\s*,?\s*net\s*(\d+)', terms)
    
    if match:
        discount_percent = float(match.group(1)) / 100.0
        discount_days = int(match.group(2))
        net_days = int(match.group(3))
        
        discount_date = inv_date + timedelta(days=discount_days)
        due_date = inv_date + timedelta(days=net_days)
        
        savings = amount * discount_percent
        
        # APR Calculation: Rate / (1 - Rate) * (365 / (NetDays - DiscDays))
        days_diff = net_days - discount_days
        if days_diff > 0:
            apr = (discount_percent / (1 - discount_percent)) * (365 / days_diff)
            
            # Hurdle Rate (e.g., 10% annual cost of capital)
            hurdle_rate = 0.10
            
            if apr > hurdle_rate:
                result["optimal_payment_date"] = discount_date.strftime("%Y-%m-%d")
                result["potential_savings"] = savings
                result["reasoning"] = f"Pay early to capture {discount_percent*100}% discount. APR {apr*100:.1f}% > 10% Hurdle."
            else:
                result["optimal_payment_date"] = due_date.strftime("%Y-%m-%d")
                result["reasoning"] = f"Pay on due date. Discount APR {apr*100:.1f}% is below hurdle rate."
        else:
             result["optimal_payment_date"] = due_date.strftime("%Y-%m-%d")
             
        result["due_date"] = due_date.strftime("%Y-%m-%d")
        result["discount_date"] = discount_date.strftime("%Y-%m-%d")
        
    # 2. Parse "Net 30" style
    elif "net" in terms:
        match_net = re.search(r'net\s*(\d+)', terms)
        if match_net:
            days = int(match_net.group(1))
            due_date = inv_date + timedelta(days=days)
            result["due_date"] = due_date.strftime("%Y-%m-%d")
            result["optimal_payment_date"] = due_date.strftime("%Y-%m-%d")
            result["reasoning"] = f"Standard Net {days} terms. Pay on due date."
            
    # Default fallback
    if not result["due_date"]:
         # Default to Net 30 if parsed terms failed but date exists
         due_date = inv_date + timedelta(days=30)
         result["due_date"] = due_date.strftime("%Y-%m-%d")
         result["optimal_payment_date"] = due_date.strftime("%Y-%m-%d")
         result["reasoning"] = "Could not parse terms, defaulting to Net 30"

    return result


def resolve_discrepancy(discrepancy_type: str, details: str, recommended_action: str) -> dict:
    """
    Autonomously resolve or outreach for a discrepancy.
    Simulates sending emails or auto-correcting based on confidence.
    """
    
    # 1. Outreach Logic (Simulation)
    if "outreach" in recommended_action.lower() or "email" in recommended_action.lower():
        return {
            "resolution_status": "outreach_sent",
            "action_taken": "Sent automated email to vendor/internal team",
            "details": f"Outreach triggered for {discrepancy_type}. Content: {details}",
            "auto_resolved": False
        }
        
    # 2. Auto-Correction Logic
    elif "correct" in recommended_action.lower() or "accept" in recommended_action.lower():
         return {
            "resolution_status": "auto_corrected",
            "action_taken": "System applied auto-correction within tolerance",
            "details": details,
            "auto_resolved": True
        }
        
    else:
        return {
            "resolution_status": "flagged_for_human",
            "action_taken": "Escalated to human review queue",
            "details": details,
            "auto_resolved": False
        }


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return result as JSON string"""
    
    if tool_name == "validate_vendor":
        result = validate_vendor(tool_input.get("vendor_name", ""))
    elif tool_name == "perform_3_way_match":
        result = perform_3_way_match(
            tool_input.get("po_number", ""),
            tool_input.get("vendor_name", ""),
            float(tool_input.get("invoice_amount", 0))
        )
    elif tool_name == "check_po": # Backwards compatibility / alias
        result = perform_3_way_match(
            tool_input.get("po_number", ""),
            tool_input.get("vendor_name", ""),
            float(tool_input.get("invoice_amount", 0))
        )
    elif tool_name == "flag_anomaly":
        result = flag_anomaly(
            tool_input.get("anomaly_type", "unknown"),
            tool_input.get("description", ""),
            tool_input.get("severity", "medium")
        )
    elif tool_name == "resolve_discrepancy":
        result = resolve_discrepancy(
            tool_input.get("discrepancy_type", ""),
            tool_input.get("details", ""),
            tool_input.get("recommended_action", "")
        )
    else:
        result = {"error": f"Unknown tool: {tool_name}"}
    
    return json.dumps(result)


def encode_image_to_base64(image_path: str) -> str:
    """Encode image file to base64"""
    with open(image_path, "rb") as image_file:
        return base64.standard_b64encode(image_file.read()).decode("utf-8")


def get_image_media_type(image_path: str) -> str:
    """Determine media type from file extension"""
    ext = Path(image_path).suffix.lower()
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".gif": "image/gif",
        ".webp": "image/webp"
    }
    return media_types.get(ext, "image/jpeg")


def convert_pdf_to_image(pdf_path: str) -> str:
    """Convert PDF to PNG image for vision processing"""
    if not PDF_SUPPORT:
        raise ImportError("pdf2image not installed. Install with: pip install pdf2image pillow")
    
    # Convert first page of PDF to image
    images = convert_from_path(pdf_path, first_page=1, last_page=1, dpi=200)
    
    if not images:
        raise ValueError(f"Could not convert PDF: {pdf_path}")
    
    # Save as temporary PNG
    temp_path = Path(pdf_path).stem + "_temp.png"
    images[0].save(temp_path, "PNG")
    
    return temp_path


def read_docx_text(file_path: str) -> str:
    """Extract text from a Word document"""
    if not DOCX_SUPPORT:
        raise ImportError("python-docx not installed. Install with: pip install python-docx")
    
    doc = docx.Document(file_path)
    full_text = []
    for para in doc.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)


def prepare_invoice_image(file_path: str) -> Tuple[str, bool]:
    """
    Prepare invoice file for processing, converting PDF to image if needed
    Returns (image_path, is_temp_file)
    """
    file_path_lower = file_path.lower()
    
    if file_path_lower.endswith('.pdf'):
        # Convert PDF to image
        image_path = convert_pdf_to_image(file_path)
        return image_path, True  # Mark as temporary
    else:
        return file_path, False  # Use as-is
    
def is_word_document(file_path: str) -> bool:
    """Check if file is a Word document"""
    ext = Path(file_path).suffix.lower()
    return ext in ['.docx', '.doc']


def process_invoice(image_path: str) -> dict:
    """
    Process an invoice image using Claude with tool use
    Returns extracted data and validation results
    """
    
    # Check if file exists
    if not Path(image_path).exists():
        return {
            "success": False,
            "error": f"File not found: {image_path}"
        }
    
    # Prepare content for Claude
    content = []
    is_temp = False
    actual_path = image_path
    
    try:
        if is_word_document(image_path):
            # Text-based processing for Word docs
            invoice_text = read_docx_text(image_path)
            content = [
                {
                    "type": "text",
                    "text": f"Please process this invoice text:\n\n{invoice_text}\n\n1. Extract: vendor name, invoice number, date, total amount, line items\n2. If there's a PO number, validate it\n3. Check if the vendor exists in our database\n4. Flag any anomalies or issues you notice\n5. Provide confidence scores (high/medium/low) for each key field\n\nAfter validation, provide the final result as structured JSON."
                }
            ]
        else:
            # Image-based processing
            actual_path, is_temp = prepare_invoice_image(image_path)
            
            # Encode image
            image_data = encode_image_to_base64(actual_path)
            media_type = get_image_media_type(actual_path)
            
            content = [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data
                    }
                },
                {
                    "type": "text",
                    "text": """Please process this invoice. Extract all key information and validate it:
                        
1. Extract: vendor name, invoice number, date, total amount, line items (if visible)
2. If there's a PO number, validate it
3. Check if the vendor exists in our database
4. Flag any anomalies or issues you notice
5. Provide confidence scores (high/medium/low) for each key field

After validation, provide the final result as structured JSON."""
                }
            ]

        # Define tools
        tools = [
            {
                "name": "validate_vendor",
                "description": "Check if a vendor exists in the company database",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "vendor_name": {
                            "type": "string",
                            "description": "The name of the vendor from the invoice"
                        }
                    },
                    "required": ["vendor_name"]
                }
            },
            {
                "name": "perform_3_way_match",
                "description": "Validate PO number, check invoice amount vs PO amount (2-way), and check invoice vs goods receipts (3-way).",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "po_number": {
                            "type": "string",
                            "description": "The PO number from the invoice"
                        },
                        "vendor_name": {
                            "type": "string",
                            "description": "The vendor name"
                        },
                        "invoice_amount": {
                            "type": "number",
                            "description": "The total invoice amount"
                        }
                    },
                    "required": ["po_number", "vendor_name", "invoice_amount"]
                }
            },
            {
                "name": "flag_anomaly",
                "description": "Flag an issue or anomaly with the invoice for human review",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "anomaly_type": {
                            "type": "string",
                            "description": "Type of anomaly (e.g., missing_vendor, amount_mismatch, missing_po)"
                        },
                        "description": {
                            "type": "string",
                            "description": "Detailed description of the anomaly"
                        },
                        "severity": {
                            "type": "string",
                            "enum": ["low", "medium", "high", "critical"],
                            "description": "Severity level of the anomaly"
                        }
                    },
                    "required": ["anomaly_type", "description"]
                }
            },
            {
                "name": "resolve_discrepancy",
                "description": "Attempt to resolve a discrepancy via autonomous outreach or auto-correction.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "discrepancy_type": {
                            "type": "string",
                            "description": "The type of issue (e.g. '3_way_failure', 'vendor_not_found')"
                        },
                        "details": {
                            "type": "string",
                            "description": "Context about the discrepancy"
                        },
                        "recommended_action": {
                            "type": "string",
                            "description": "Action to take: 'outreach_vendor', 'email_purchasing', 'auto_correct', 'escalate'"
                        }
                    },
                    "required": ["discrepancy_type", "details", "recommended_action"]
                }
            },
            {
                "name": "optimize_payment",
                "description": "Calculate the optimal payment date based on payment terms (e.g. 2/10 Net 30) and invoice details.",
                "input_schema": {
                    "type": "object",
                    "properties": {
                        "payment_terms": {
                            "type": "string",
                            "description": "Payment terms string (e.g. 'Net 30', '2/10 Net 30')"
                        },
                        "invoice_date": {
                            "type": "string",
                            "description": "Invoice date in YYYY-MM-DD format"
                        },
                        "invoice_amount": {
                            "type": "number",
                            "description": "Total invoice amount"
                        }
                    },
                    "required": ["payment_terms", "invoice_date", "invoice_amount"]
                }
            }
        ]
        
        # Initial system prompt
        system_prompt = """You are an expert Autonomous Invoice Processing Agent. Your job is to:

1. Extract key invoice information: vendor, invoice #, date, amount, line items, PO #.
2. **Extract Payment Terms**: Look for "Net 30", "2/10", etc.
3. Validate using available tools:
   - `validate_vendor`
   - `perform_3_way_match`
4. **Optimize Payment**: 
   - Use `optimize_payment` tool if payment terms are found.
   - This helps us decide when to pay to capture discounts.
5. Handle Discrepancies recursively.
6. Output structured JSON.

Always try to find the "Optimal Payment Date"."""

        # Initial message to Claude
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        
        # Agentic loop
        final_result = None
        max_iterations = 10
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            
            # Call Claude
            response = client.messages.create(
                model=DEFAULT_MODEL,
                max_tokens=MAX_TOKENS,
                tools=tools,
                messages=messages,
                system=system_prompt
            )
            
            # Check stop reason
            if response.stop_reason == "tool_use":
                # Process tool calls
                tool_results = []
                
                for block in response.content:
                    if block.type == "tool_use":
                        tool_name = block.name
                        tool_input = block.input
                        tool_use_id = block.id
                        
                        # Execute tool
                        result_str = execute_tool(tool_name, tool_input)
                        
                        # Add tool result
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
                            "content": result_str
                        })
                
                # Add assistant response
                messages.append({
                    "role": "assistant",
                    "content": response.content
                })
                
                # Add tool results to messages
                if tool_results:
                    messages.append({
                        "role": "user",
                        "content": tool_results
                    })
            elif response.stop_reason == "end_turn":
                # Extract final result from response
                for block in response.content:
                    if hasattr(block, 'text'):
                        try:
                            json_match = re.search(r'\{[\s\S]*\}', block.text)
                            if json_match:
                                final_result = json.loads(json_match.group())
                                break
                        except json.JSONDecodeError:
                            pass
                break
            else:
                # Unexpected stop reason
                break
        
        # Parse final result if not already done
            if final_result is None:
                final_result = {
                    "success": False,
                    "error": "Could not extract structured result from agent"
                }
        # Add success indicator
        if "success" not in final_result:
            final_result["success"] = True
            
        # SAVE TO DB
        final_result = save_invoice_to_db(final_result)
        
        return final_result
        
    except Exception as e:
        return {
            "success": False,
            "error": f"An unexpected error occurred: {str(e)}"
        }
    finally:
        # Clean up temporary file if it was created
        if is_temp and actual_path:
            try:
                Path(actual_path).unlink()
            except Exception:
                pass


def save_invoice_to_db(data: dict) -> dict:
    """Save processed invoice data to database"""
    # Import locally to avoid circular imports if any, or just for safety
    from models import Vendor, PurchaseOrder, Invoice, InvoiceLine
    
    db = SessionLocal()
    try:
        # Extract fields
        extracted = data.get("extraction_results", data.get("extracted_data", {}))
        if not extracted:
            return data
            
        # Get/Find Vendor
        vendor_name = extracted.get("vendor_name")
        vendor_id = None
        if vendor_name:
            if isinstance(vendor_name, dict):
                vendor_name = vendor_name.get("value") or vendor_name.get("name") or str(vendor_name)
            
            if isinstance(vendor_name, str):
                # Try to find vendor
                v = db.query(Vendor).filter(Vendor.name.ilike(vendor_name.strip())).first()
                if v:
                    vendor_id = v.id
        
        # Parse Amount
        try:
            amt = float(extracted.get("total_amount", 0))
        except:
            amt = 0.0
            
        # Create Invoice Record
        new_inv = Invoice(
            invoice_number=extracted.get("invoice_number"),
            vendor_id=vendor_id,
            date=extracted.get("invoice_date"),
            total_amount=amt,
            status="processed", # Default status
            
            # Payment Opt Fields
            payment_terms=extracted.get("payment_terms"),
            due_date=extracted.get("due_date"),
            discount_date=extracted.get("discount_date"),
            optimal_payment_date=extracted.get("optimal_payment_date"),
            potential_savings=float(extracted.get("potential_savings", 0) or 0),
            
            extracted_data=data
        )
        db.add(new_inv)
        db.flush() # Get ID
        
        # Save Line Items
        lines = extracted.get("line_items", [])
        for line in lines:
            inv_line = InvoiceLine(
                invoice_id=new_inv.id,
                description=line.get("description", ""),
                quantity=float(line.get("quantity", 0) or 0),
                unit_price=float(line.get("unit_price", 0) or 0),
                total=float(line.get("total", 0) or 0)
            )
            db.add(inv_line)
            
        db.commit()
        data["db_saved"] = True
        data["invoice_db_id"] = new_inv.id
        return data
        
    except Exception as e:
        print(f"Error saving to DB: {e}")
        data["db_error"] = str(e)
        return data
    finally:
        db.close()


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        invoice_path = sys.argv[1]
        print(f"Processing: {invoice_path}")
        result = process_invoice(invoice_path)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python invoice_agent.py <invoice_path>")
