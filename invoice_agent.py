"""
Invoice Processing Agent using Claude with Tool Use
Extracts invoice data, validates, and flags anomalies
Supports PDF files by converting them to images
"""

import anthropic
import base64
import json
import re
from datetime import datetime
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
from models import Vendor, PurchaseOrder, Invoice, InvoiceLine
from sqlalchemy import or_


def validate_vendor(vendor_name: str) -> dict:
    """Check if vendor exists in database"""
    vendor_clean = vendor_name.strip()
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


def check_po(po_number: str, vendor_name: str, invoice_amount: float) -> dict:
    """Validate PO number and check amount"""
    
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
        
        # Check vendor match
        # We need to get the linked vendor name
        po_vendor = po_obj.vendor
        
        vendor_match = False
        if po_vendor:
            v_name_db = po_vendor.name.lower()
            v_name_inv = vendor_name.lower()
            # Simple containment check
            if v_name_db in v_name_inv or v_name_inv in v_name_db:
                vendor_match = True
        
        if not vendor_match:
             return {
                "valid": False,
                "message": f"Vendor mismatch: Invoice from '{vendor_name}' but PO is for '{po_vendor.name if po_vendor else 'Unknown'}'",
                "po_found": True,
                "vendor_match": False
            }
        
        # Check amount tolerance
        expected = po_obj.expected_amount
        tolerance = po_obj.tolerance
        tolerance_amount = expected * tolerance
        
        if invoice_amount < expected - tolerance_amount or invoice_amount > expected + tolerance_amount:
            return {
                "valid": False,
                "message": f"Amount mismatch: Invoice ${invoice_amount} exceeds PO tolerance (expected ${expected} ±${tolerance_amount})",
                "po_found": True,
                "vendor_match": True,
                "amount_in_tolerance": False,
                "expected_amount": expected,
                "tolerance_percentage": tolerance * 100
            }
        
        return {
            "valid": True,
            "message": f"PO '{po_number}' validated successfully",
            "po_found": True,
            "vendor_match": True,
            "amount_in_tolerance": True,
            "expected_amount": expected
        }
            
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


def execute_tool(tool_name: str, tool_input: dict) -> str:
    """Execute a tool and return result as JSON string"""
    
    if tool_name == "validate_vendor":
        result = validate_vendor(tool_input.get("vendor_name", ""))
    elif tool_name == "check_po":
        result = check_po(
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
                "name": "check_po",
                "description": "Validate a PO number and check invoice amount against expected amount",
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
            }
        ]
        
        # Initial system prompt
        system_prompt = """You are an expert invoice processing agent. Your job is to:

1. Extract key invoice information: vendor name, invoice number, date, total amount, line items, and PO number
2. Validate the data by:
   - Checking if the vendor exists in our database
   - Validating PO numbers if present
   - Flagging any anomalies or issues
3. Provide confidence scores for extracted fields
4. Output structured JSON with all extracted data and validation results

Be thorough but efficient. Ask clarification questions if data is ambiguous or missing.
Always validate critical fields before proceeding.
Flag anything unusual for human review."""

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
