"""
Streamlit interface for Invoice Processing Agent
Provides UI for uploading invoices and viewing results
"""

import streamlit as st
import json
from pathlib import Path
import tempfile
from invoice_agent import process_invoice
import pandas as pd

# Page configuration
st.set_page_config(
    page_title="Invoice Processing Agent",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .header {
        padding: 20px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 30px;
    }
    .status-success {
        padding: 15px;
        background-color: #d4edda;
        border-left: 4px solid #28a745;
        border-radius: 4px;
        color: #155724;
    }
    .status-warning {
        padding: 15px;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        border-radius: 4px;
        color: #856404;
    }
    .status-error {
        padding: 15px;
        background-color: #f8d7da;
        border-left: 4px solid #dc3545;
        border-radius: 4px;
        color: #721c24;
    }
    .metric-card {
        padding: 15px;
        background-color: #f8f9fa;
        border-radius: 8px;
        border: 1px solid #dee2e6;
    }
    .field-table {
        width: 100%;
        border-collapse: collapse;
    }
    .field-table th {
        background-color: #667eea;
        color: white;
        padding: 12px;
        text-align: left;
    }
    .field-table td {
        padding: 12px;
        border-bottom: 1px solid #dee2e6;
    }
    .field-table tr:hover {
        background-color: #f8f9fa;
    }
    .confidence-high {
        color: #28a745;
        font-weight: bold;
    }
    .confidence-medium {
        color: #ffc107;
        font-weight: bold;
    }
    .confidence-low {
        color: #dc3545;
        font-weight: bold;
    }
    .anomaly-item {
        padding: 12px;
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        margin-bottom: 10px;
        border-radius: 4px;
    }
    .anomaly-critical {
        background-color: #f8d7da;
        border-left-color: #dc3545;
    }
    .json-output {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 4px;
        padding: 15px;
        font-family: monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }
</style>
""", unsafe_allow_html=True)

# Header
st.markdown("""
<div class="header">
    <h1>📄 Invoice Processing Agent</h1>
    <p>AI-powered invoice extraction, validation, and anomaly detection</p>
</div>
""", unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.header("About")
    st.info(
        """
        **Invoice Processing Agent** uses Claude's vision capabilities to:
        
        • Extract invoice data (vendor, amount, date, line items)
        • Validate against business rules
        • Flag anomalies and discrepancies
        • Provide confidence scores
        • Generate audit-ready JSON output
        
       **Invoice Processing Agent** | Built by Zillion Technologies  
        """
    )
    
    st.divider()
    
    st.subheader("Sample Invoices")
    st.write("Try these scenarios:")
    st.markdown("""
    - ✅ **Clean Invoice**: Standard format, all fields present
    - ⚠️ **Missing Data**: Some fields absent or unclear
    - 🚩 **Discrepancy**: Amount or vendor mismatch
    - 🔄 **Edge Case**: Unusual format or structure
    """)
    
    st.divider()
    
    st.subheader("How it Works")
    st.markdown("""
    1. Upload invoice image/PDF
    2. Agent extracts key data
    3. Validation checks run automatically
    4. Results displayed with confidence scores
    5. Export as JSON for downstream systems
    """)

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("Upload Invoice")
    
    uploaded_file = st.file_uploader(
        "Choose an invoice image or PDF",
        type=["jpg", "jpeg", "png", "gif", "webp", "pdf"],
        help="Upload invoice image or PDF for processing"
    )
    
    if uploaded_file is not None:
        # Display uploaded file info
        st.caption(f"File: {uploaded_file.name}")
        
        # Show preview for images
        if uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, caption="Invoice Preview", use_container_width=True)

with col2:
    st.subheader("Quick Start")
    
    st.write("**No invoice to test?** Here's what the system does:")
    
    st.code("""
# System automatically:
✓ Extracts vendor, amount, date
✓ Validates PO numbers
✓ Checks vendor database
✓ Flags discrepancies
✓ Scores confidence (H/M/L)
✓ Outputs clean JSON
    """, language="text")

# Processing
if uploaded_file is not None:
    if st.button("Process Invoice", type="primary", use_container_width=True):
        with st.spinner("Processing invoice with Claude Agent..."):
            # Save uploaded file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                tmp_file.write(uploaded_file.getbuffer())
                tmp_path = tmp_file.name
            
            try:
                # Process invoice
                result = process_invoice(tmp_path)
                
                # Store in session state for display
                st.session_state.last_result = result
                st.session_state.filename = uploaded_file.name
                
            except Exception as e:
                st.error(f"Error processing invoice: {str(e)}")
            finally:
                # Clean up temp file
                Path(tmp_path).unlink(missing_ok=True)

# Display results if available
if "last_result" in st.session_state:
    result = st.session_state.last_result
    filename = st.session_state.filename
    
    st.divider()
    st.subheader(f"Processing Results: {filename}")
    
    # Status
    if result.get("success", False):
        st.markdown("""
        <div class="status-success">
        ✅ Invoice processed successfully
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="status-error">
        ❌ Error processing invoice
        </div>
        """, unsafe_allow_html=True)
        if "error" in result:
            st.error(result["error"])
        st.stop()
    
    # Results in tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Extracted Data", "Validation", "Anomalies", "JSON Output"])
    
    with tab1:
        st.subheader("Extracted Invoice Data")
        
        # Handle different JSON structures from Claude
        if "extraction_results" in result:
            # New Claude format
            extracted = result.get("extraction_results", {})
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                inv_num = extracted.get("invoice_number", {})
                if isinstance(inv_num, dict):
                    inv_num_val = inv_num.get("value", "N/A")
                    inv_num_conf = inv_num.get("confidence", "N/A")
                else:
                    inv_num_val = inv_num
                    inv_num_conf = "N/A"
                
                st.metric(
                    "Invoice Number",
                    inv_num_val,
                    delta=f"Confidence: {inv_num_conf}"
                )
            
            with col2:
                inv_date = extracted.get("invoice_date", {})
                if isinstance(inv_date, dict):
                    inv_date_val = inv_date.get("value", "N/A")
                    inv_date_conf = inv_date.get("confidence", "N/A")
                else:
                    inv_date_val = inv_date
                    inv_date_conf = "N/A"
                
                st.metric(
                    "Invoice Date",
                    inv_date_val,
                    delta=f"Confidence: {inv_date_conf}"
                )
            
            with col3:
                total = extracted.get("total_amount", {})
                if isinstance(total, dict):
                    total_val = total.get("value", 0)
                    total_conf = total.get("confidence", "N/A")
                else:
                    total_val = total
                    total_conf = "N/A"
                
                st.metric(
                    "Total Amount",
                    f"${float(total_val):,.2f}",
                    delta=f"Confidence: {total_conf}"
                )
            
            st.divider()
            
            # Vendor info
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Vendor Name**")
                vendor = extracted.get("vendor_name", {})
                if isinstance(vendor, dict):
                    st.write(vendor.get("value", "N/A"))
                else:
                    st.write(vendor)
            
            with col2:
                st.write("**PO Number**")
                po = extracted.get("po_number", {})
                if isinstance(po, dict):
                    st.write(po.get("value", "N/A"))
                else:
                    st.write(po)
            
            st.divider()
            
            # Line items
            st.write("**Line Items**")
            line_items = extracted.get("line_items", [])
            if line_items:
                for item in line_items:
                    if isinstance(item, dict):
                        desc = item.get("description", "N/A")
                        amount = item.get("amount", 0)
                        conf = item.get("confidence", "N/A")
                        st.write(f"• {desc}: ${float(amount):,.2f} ({conf})")
            else:
                st.write("No line items found")
        
        else:
            # Fallback for old format
            extracted = result.get("extracted_data", {})
            st.caption(f"Confidence: {extracted.get('vendor_name_confidence', 'N/A')}")
        
        with col2:
            st.write("**PO Number**")
            st.write(extracted.get("po_number", "N/A"))
            st.caption(f"Confidence: {extracted.get('po_number_confidence', 'N/A')}")
        
        st.divider()
        
        # Line items
        if extracted.get("line_items"):
            st.write("**Line Items**")
            
            items_data = []
            for item in extracted.get("line_items", []):
                items_data.append({
                    "Description": item.get("description", "N/A"),
                    "Qty": item.get("quantity", "N/A"),
                    "Unit Price": f"${item.get('unit_price', 0):.2f}",
                    "Total": f"${item.get('total', 0):.2f}"
                })
            
            if items_data:
                st.dataframe(pd.DataFrame(items_data), use_container_width=True)
    
    with tab2:
        st.subheader("Validation Results")
        
        # Handle new structure with validation_results
        if "validation_results" in result:
            validations = result.get("validation_results", {})
            
            # Vendor validation
            vendor_val = validations.get("vendor_validation", {})
            if vendor_val.get("valid"):
                st.markdown(f"""
                <div class="status-success">
                ✅ **Vendor Valid**: {vendor_val.get("message", "")}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-warning">
                ⚠️ **Vendor Issue**: {vendor_val.get("message", "")}
                </div>
                """, unsafe_allow_html=True)
            
            # PO validation
            st.divider()
            po_val = validations.get("po_validation", {})
            if po_val.get("valid"):
                st.markdown(f"""
                <div class="status-success">
                ✅ **PO Valid**: {po_val.get("message", "")}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class="status-warning">
                ⚠️ **PO Issue**: {po_val.get("message", "")}
                </div>
                """, unsafe_allow_html=True)
        else:
            # Fallback for old structure
            validations = result.get("validations", {})
    
    with tab3:
        st.subheader("Flagged Anomalies")
        
        anomalies = result.get("anomalies", [])
        
        if not anomalies:
            st.success("No anomalies detected - invoice looks clean")
        else:
            for idx, anomaly in enumerate(anomalies, 1):
                severity = anomaly.get("severity", "medium")
                anomaly_type = anomaly.get("type", "unknown")
                description = anomaly.get("description", "")
                
                severity_class = f"anomaly-item anomaly-{severity}" if severity == "critical" else "anomaly-item"
                
                severity_emoji = {
                    "low": "ℹ️",
                    "medium": "⚠️",
                    "high": "🚩",
                    "critical": "🔴"
                }.get(severity, "⚠️")
                
                st.markdown(f"""
                <div class="{severity_class}">
                <strong>{severity_emoji} {anomaly_type.upper()}</strong><br>
                {description}<br>
                <small>Severity: {severity.upper()}</small>
                </div>
                """, unsafe_allow_html=True)
    
    with tab4:
        st.subheader("Full JSON Output")
        st.caption("Ready for integration with downstream systems")
        
        # Pretty print JSON
        json_str = json.dumps(result, indent=2)
        st.code(json_str, language="json")
        
        # Download button
        st.download_button(
            label="Download JSON",
            data=json_str,
            file_name=f"invoice_result_{st.session_state.filename.split('.')[0]}.json",
            mime="application/json"
        )
    
    st.divider()
    
    # Action buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.button("✅ Approve Invoice", use_container_width=True):
            st.success("Invoice marked as approved!")
    
    with col2:
        if st.button("📋 Needs Review", use_container_width=True):
            st.info("Invoice flagged for manual review")
    
    with col3:
        if st.button("❌ Reject", use_container_width=True):
            st.error("Invoice rejected")
    
    with col4:
        if st.button("🔄 Process Another", use_container_width=True):
            del st.session_state.last_result
            st.rerun()

# Footer
st.divider()
st.markdown("""
---
**Invoice Processing Agent** | Built by Zillion Technologies  
*Agentic AI for Enterprise RFP Response & Automation*  
Demo v1.0 | Production-Ready Framework
""")
