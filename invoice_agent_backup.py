"""
Invoice Processing Agent using Claude with Tool Use
Extracts invoice data, validates, and flags anomalies
"""

import anthropic
import base64
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import mimetypes
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize Anthropic client - explicitly use API key from environment
api_key = os.getenv('ANTHROPIC_API_KEY')
if not api_key:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please set it in your .env file.")
client = anthropic.Anthropic(api_key=api_key)

# Model configuration - can be overridden via environment variable
DEFAULT_MODEL = os.getenv('INVOICE_MODEL', 'claude-3-5-sonnet-20241022')
MAX_TOKENS = int(os.getenv('MAX_TOKENS', '2048'))

# Dummy vendor database - in production this would be a real database
VENDOR_DATABASE = {
    "acme corp": {"id": "V001", "category": "supplies"},
    "tech solutions inc": {"id": "V002", "category": "software"},
    "office depot": {"id": "V003", "category": "supplies"},
    "aws": {"id": "V004", "category": "cloud services"},
    "microsoft": {"id": "V005", "category": "software"},
    "fedex": {"id": "V006", "category": "shipping"},
    "usps": {"id": "V007", "category": "shipping"},
    "ups": {"id": "V008", "category": "shipping"},
    "dell": {"id": "V009", "category": "hardware"},
    "hp": {"id": "V010", "category": "hardware"},
    "cisco": {"id": "V011", "category": "networking"},
    "salesforce": {"id": "V012", "category": "software"},
    "slack": {"id": "V013", "category": "software"},
    "stripe": {"id": "V014", "category": "payment processing"},
    "twilio": {"id": "V015", "category": "communications"},
}

# PO database - maps PO numbers to expected amounts (with tolerance)
PO_DATABASE = {
    "PO-2024-001": {"vendor": "acme corp", "expected_amount": 5000, "tolerance": 0.1},
    "PO-2024-002": {"vendor": "tech solutions inc", "expected_amount": 15000, "tolerance": 0.1},
    "PO-2024-003": {"vendor": "office depot", "expected_amount": 2500, "tolerance": 0.1},
    "PO-2024-004": {"vendor": "aws", "expected_amount": 8500, "tolerance": 0.15},
}


def validate_vendor(vendor_name: str) -> dict:
    """Check if vendor exists in database"""
    vendor_lower = vendor_name.lower().strip()
    
    # Exact match
    if vendor_lower in VENDOR_DATABASE:
        return {
            "valid": True,
            "vendor_id": VENDOR_DATABASE[vendor_lower]["id"],
            "category": VENDOR_DATABASE[vendor_lower]["category"],
            "message": f"Vendor '{vendor_name}' found in database"
        }
    
    # Fuzzy match (check if vendor name contains or is contained in database)
    for db_vendor in VENDOR_DATABASE.keys():
        if vendor_lower in db_vendor or db_vendor in vendor_lower:
            return {
                "valid": True,
                "vendor_id": VENDOR_DATABASE[db_vendor]["id"],
                "category": VENDOR_DATABASE[db_vendor]["category"],
                "message": f"Vendor matched to '{db_vendor}' in database",
                "match_type": "fuzzy"
            }
    
    return {
        "valid": False,
        "message": f"Vendor '{vendor_name}' not found in database - flagged for review",
        "suggestion": "Verify vendor and add to database if legitimate"
    }


def check_po(po_number: str, vendor_name: str, invoice_amount: float) -> dict:
    """Validate PO number and check amount matches"""
    po_upper = po_number.strip().upper()
    
    if po_upper not in PO_DATABASE:
        return {
            "valid": False,
            "message": f"PO {po_upper} not found in database",
            "type": "missing_po"
        }
    
    po_info = PO_DATABASE[po_upper]
    expected_vendor = po_info["vendor"].lower()
    vendor_lower = vendor_name.lower().strip()
    
    # Check vendor matches PO
    if expected_vendor not in vendor_lower and vendor_lower not in expected_vendor:
        return {
            "valid": False,
            "message": f"Vendor mismatch: PO {po_upper} is for '{po_info['vendor']}' but invoice is from '{vendor_name}'",
            "type": "vendor_mismatch",
            "expected_vendor": po_info["vendor"],
            "actual_vendor": vendor_name
        }
    
    # Check amount is within tolerance
    expected_amount = po_info["expected_amount"]
    tolerance = po_info["tolerance"]
    min_amount = expected_amount * (1 - tolerance)
    max_amount = expected_amount * (1 + tolerance)
    
    if not (min_amount <= invoice_amount <= max_amount):
        return {
            "valid": False,
            "message": f"Amount mismatch: PO {po_upper} expected ${expected_amount:.2f} ±{tolerance*100:.0f}%, got ${invoice_amount:.2f}",
            "type": "amount_mismatch",
            "expected_amount": expected_amount,
            "actual_amount": invoice_amount,
            "variance_percent": ((invoice_amount - expected_amount) / expected_amount * 100)
        }
    
    return {
        "valid": True,
        "message": f"PO {po_upper} validated successfully",
        "expected_amount": expected_amount,
        "actual_amount": invoice_amount
    }


def flag_anomaly(anomaly_type: str, description: str, severity: str = "medium") -> dict:
    """Record an anomaly or issue with the invoice"""
    return {
        "flagged": True,
        "type": anomaly_type,
        "description": description,
        "severity": severity,  # low, medium, high, critical
        "timestamp": datetime.now().isoformat()
    }


def process_tool_call(tool_name: str, tool_input: dict) -> str:
    """Execute tool calls from the agent"""
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
    
    # Encode image
    image_data = encode_image_to_base64(image_path)
    media_type = get_image_media_type(image_path)
    
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
            "description": "Validate a PO number and check if invoice amount matches expected amount",
            "input_schema": {
                "type": "object",
                "properties": {
                    "po_number": {
                        "type": "string",
                        "description": "The PO (Purchase Order) number from the invoice"
                    },
                    "vendor_name": {
                        "type": "string",
                        "description": "The vendor name from the invoice"
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
            "description": "Flag an issue or anomaly found in the invoice",
            "input_schema": {
                "type": "object",
                "properties": {
                    "anomaly_type": {
                        "type": "string",
                        "description": "Type of anomaly (e.g., 'missing_field', 'unusual_amount', 'duplicate')"
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
            "content": [
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
            model="claude-opus-4-1-20250805",
            max_tokens=2048,
            system=system_prompt,
            tools=tools,
            messages=messages
        )
        
        # Check if we're done
        if response.stop_reason == "end_turn":
            # Extract final text response
            for block in response.content:
                if hasattr(block, 'text'):
                    try:
                        # Try to parse JSON from response
                        json_match = re.search(r'\{[\s\S]*\}', block.text)
                        if json_match:
                            final_result = json.loads(json_match.group())
                    except json.JSONDecodeError:
                        pass
            break
        
        # Process tool calls
        if response.stop_reason == "tool_use":
            # Add assistant response to messages
            messages.append({
                "role": "assistant",
                "content": response.content
            })
            
            # Process each tool call
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    tool_result = process_tool_call(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": tool_result
                    })
            
            # Add tool results to messages
            if tool_results:
                messages.append({
                    "role": "user",
                    "content": tool_results
                })
        else:
            # Unexpected stop reason
            break
    
    # Parse final result if not already done
    if final_result is None:
        # Try to extract from last message
        for block in response.content:
            if hasattr(block, 'text'):
                try:
                    json_match = re.search(r'\{[\s\S]*\}', block.text)
                    if json_match:
                        final_result = json.loads(json_match.group())
                except json.JSONDecodeError:
                    pass
        
        if final_result is None:
            final_result = {
                "success": False,
                "error": "Could not extract structured result from agent"
            }
    
    # Add success indicator
    if "success" not in final_result:
        final_result["success"] = True
    
    return final_result


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) > 1:
        image_path = sys.argv[1]
        result = process_invoice(image_path)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python invoice_agent.py <image_path>")
