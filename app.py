"""
Streamlit interface for Invoice Processing Agent
Professional Commercial Design
"""

import streamlit as st
import json
from pathlib import Path
import tempfile
from invoice_agent import process_invoice
import pandas as pd
from quickbooks_manager import QuickBooksManager
from xero_manager import XeroManager
from netsuite_manager import NetSuiteManager
import os
from dotenv import load_dotenv
from database import engine, SessionLocal, Base
from models import Vendor, PurchaseOrder

# Initialize DB
Base.metadata.create_all(bind=engine)

def seed_data():
    db = SessionLocal()
    if db.query(Vendor).count() == 0:
        # Seed Vendors
        vendors = [
            Vendor(vendor_id="V001", name="Acme Corp", category="supplies"),
            Vendor(vendor_id="V002", name="Tech Solutions Inc", category="software"),
            Vendor(vendor_id="V003", name="Office Depot", category="supplies"),
            Vendor(vendor_id="V004", name="AWS", category="cloud services"),
            Vendor(vendor_id="V005", name="Microsoft", category="software"),
        ]
        db.add_all(vendors)
        db.commit()
            
        # Seed POs
        # Need to query vendors to get IDs
        acme = db.query(Vendor).filter_by(name="Acme Corp").first()
        tech = db.query(Vendor).filter_by(name="Tech Solutions Inc").first()
        office = db.query(Vendor).filter_by(name="Office Depot").first()
        aws = db.query(Vendor).filter_by(name="AWS").first()
        
        pos = [
            PurchaseOrder(po_number="PO-2024-001", vendor_id=acme.id, expected_amount=5000.0, tolerance=0.1),
            PurchaseOrder(po_number="PO-2024-002", vendor_id=tech.id, expected_amount=15000.0, tolerance=0.1),
            PurchaseOrder(po_number="PO-2024-003", vendor_id=office.id, expected_amount=2500.0, tolerance=0.1),
            PurchaseOrder(po_number="PO-2024-004", vendor_id=aws.id, expected_amount=8500.0, tolerance=0.15),
        ]
        db.add_all(pos)
        db.commit()
    db.close()

seed_data()

load_dotenv()

# Page configuration
st.set_page_config(
    page_title="InvoiceAI Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# Custom CSS: Commercial/SaaS Aesthetics
# -----------------------------------------------------------------------------
st.markdown("""
<style>
    /* Global Clean Font */
    html, body, [class*="css"] {
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    
    /* Brand Colors */
    :root {
        --primary-blue: #2c3e50;
        --accent-red: #e74c3c;
        --bg-color: #f8f9fa;
    }
    
    /* Navbar / Header */
    .saas-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 1.5rem;
        background: white;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 2rem;
    }
    
    .logo-text {
        font-weight: 800;
        font-size: 1.8rem;
        color: var(--primary-blue);
        letter-spacing: -0.5px;
    }
    
    .tagline {
        font-size: 0.9rem;
        color: #7f8c8d;
    }

    /* Cards */
    .metric-container {
        background-color: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.04);
        border: 1px solid #edf2f7;
        text-align: center;
        transition: transform 0.2s ease;
    }
    
    .metric-container:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.08);
    }
    
    .metric-label {
        color: #95a5a6;
        font-size: 0.75rem;
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        color: var(--primary-blue);
        font-size: 2rem;
        font-weight: 700;
    }

    /* Custom Buttons - Red Accent */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: none;
        transition: all 0.2s;
    }
    
    div[data-testid="stButton"] > button[kind="primary"] {
        background-color: var(--accent-red);
    }
    
    div[data-testid="stButton"] > button[kind="primary"]:hover {
        background-color: #c0392b;
    }
    
    /* Document Viewer */
    .document-viewer {
        background: white;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        height: 80vh;
        overflow-y: auto;
        padding: 1rem;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Sidebar: Settings
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    
    # ERP Integration
    erp_system = st.selectbox("ERP System", ["QuickBooks Online", "Xero", "NetSuite"], index=0)
    
    with st.expander(f"{erp_system} Connection", expanded=False):
        
        # ------------------ QUICKBOOKS ------------------
        if erp_system == "QuickBooks Online":
            qb_client_id = st.text_input("QB Client ID", value=os.getenv("AB_CLIENT_ID", ""), type="password")
            qb_client_secret = st.text_input("QB Client Secret", value=os.getenv("AB_CLIENT_SECRET", ""), type="password")
            qb_redirect = st.text_input("Redirect URI", value=os.getenv("AB_REDIRECT_URI", "http://localhost:8501"))
            
            if "qb_manager" not in st.session_state and qb_client_id and qb_client_secret:
                is_mock = (qb_client_id.lower() == "mock")
                st.session_state.qb_manager = QuickBooksManager(qb_client_id, qb_client_secret, qb_redirect, mock_mode=is_mock)
                st.session_state.active_erp = "qb_manager"

            if "qb_manager" in st.session_state:
                mgr = st.session_state.qb_manager
                # Auth Callback
                qp = st.query_params
                if "code" in qp and "realmId" in qp and not mgr.is_connected():
                    try:
                        mgr.handle_callback(qp["code"], qp["realmId"])
                        st.success("Linked QB")
                    except: pass
                
                if mgr.is_connected():
                    st.success("🟢 Connected (Mock)" if mgr.mock_mode else "🟢 Connected")
                    if st.button("Disconnect QB"):
                        del st.session_state.qb_manager
                        st.rerun()
                else:
                    if getattr(mgr, 'mock_mode', False):
                        if st.button("Simulate QB Connect"):
                            mgr.handle_callback("mock", "mock")
                            st.rerun()
                    else:
                        st.link_button("Login to Intuit", mgr.get_auth_url())

        # ------------------ XERO ------------------
        elif erp_system == "Xero":
            x_client_id = st.text_input("Xero Client ID", value="mock", type="password")
            x_client_secret = st.text_input("Xero Secret", value="mock", type="password")
            
            if "xero_manager" not in st.session_state and x_client_id:
                is_mock = (x_client_id.lower() == "mock")
                st.session_state.xero_manager = XeroManager(x_client_id, x_client_secret, "http://localhost:8501", mock_mode=is_mock)
                st.session_state.active_erp = "xero_manager"

            if "xero_manager" in st.session_state:
                mgr = st.session_state.xero_manager
                if mgr.is_connected():
                    st.success("🟢 Connected (Mock)" if mgr.mock_mode else "🟢 Connected")
                    if st.button("Disconnect Xero"):
                        del st.session_state.xero_manager
                        st.rerun()
                else:
                    if getattr(mgr, 'mock_mode', False):
                        if st.button("Simulate Xero Connect"):
                            mgr.handle_callback("mock")
                            st.rerun()

        # ------------------ NETSUITE ------------------
        elif erp_system == "NetSuite":
            ns_account = st.text_input("Account ID", value="mock")
            ns_key = st.text_input("Consumer Key", value="mock", type="password")
            
            if "ns_manager" not in st.session_state and ns_account:
                is_mock = (ns_account.lower() == "mock")
                st.session_state.ns_manager = NetSuiteManager(ns_account, ns_key, "s", "t", "s", mock_mode=is_mock)
                st.session_state.active_erp = "ns_manager"

            if "ns_manager" in st.session_state:
                mgr = st.session_state.ns_manager
                if mgr.is_connected():
                    st.success("🟢 Connected (Mock)" if mgr.mock_mode else "🟢 Connected")
                    if st.button("Disconnect NetSuite"):
                        del st.session_state.ns_manager
                        st.rerun()
                else:
                    if st.button("Test Connection"):
                        if mgr.connect():
                            st.rerun()
                        else:
                            st.error("Connection Failed")

    st.divider()
    # Logo Area
    if os.path.exists("assets/logo.png"):
        st.image("assets/logo.png", use_container_width=True)
    else:
        st.markdown("## ⚡ InvoiceAI")
        
    st.write("") # Spacer
    st.write("") 
    
    st.markdown("### 🧭 Navigation")
    
    page = st.radio(
        "Go to",
        ["Dashboard", "Vendors", "Purchase Orders", "Optimization", "AI Assistant", "History", "Analytics"],
        index=0,
        label_visibility="collapsed"
    )

    st.caption("Enterprise InvoiceAI v2.0")
    st.caption("Zillion Technologies")


# -----------------------------------------------------------------------------
# Main Application Header
# -----------------------------------------------------------------------------
st.markdown("""
    <div class="saas-header">
        <div>
            <div class="logo-text">Zillion InvoiceAI</div>
            <div class="tagline">Thought beyond the DOT</div>
        </div>
        <div style="background:#eef2f7; padding:0.5rem 1rem; border-radius:20px; color:#2c3e50; font-weight:600; font-size:0.9rem;">
            Workspace: <b>Default</b>
        </div>
    </div>
""", unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# State Management & Helpers
# -----------------------------------------------------------------------------
if "current_file" not in st.session_state:
    st.session_state.current_file = None
if "processing_result" not in st.session_state:
    st.session_state.processing_result = None

def reset_state():
    st.session_state.processing_result = None
    st.session_state.current_file = None

# -----------------------------------------------------------------------------
# Routing
# -----------------------------------------------------------------------------

if page == "Vendors":
    from pages_ui.vendors import render_vendors_page
    render_vendors_page()

elif page == "Purchase Orders":
    from pages_ui.pos import render_pos_page
    render_pos_page()

elif page == "Optimization":
    from pages_ui.optimization import render_optimization_page
    render_optimization_page()

elif page == "AI Assistant":
    from pages_ui.chat import render as render_chat_page
    render_chat_page()

elif page == "History":
    from pages_ui.history import render_history_page
    render_history_page()

elif page == "Analytics":
    from pages_ui.analytics import render_analytics_page
    render_analytics_page()

else:
    # -----------------------------------------------------------------------------
    # Dashboard (Original View)
    # -----------------------------------------------------------------------------
    if st.session_state.processing_result is None:
        st.markdown("### 📂 Upload Documents")
        st.markdown("Drag and drop your invoices here to automatically extract data.")
        
        uploaded_file = st.file_uploader(
            "Upload Invoice", 
            type=["jpg", "png", "pdf", "docx"], 
            label_visibility="collapsed"
        )

        if uploaded_file:
             # Process Logic
            if st.button("✨ Process Document", type="primary"):
                with st.spinner("Analyzing document structure..."):
                    # Temp Save
                    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
                        tmp_file.write(uploaded_file.getbuffer())
                        tmp_path = tmp_file.name
                    
                    try:
                        result = process_invoice(tmp_path)
                        st.session_state.processing_result = result
                        st.session_state.current_file = uploaded_file
                        st.rerun()
                    except Exception as e:
                        st.error(f"Processing Failed: {e}")
                    finally:
                        Path(tmp_path).unlink(missing_ok=True)
                        
        # Features Grid
        st.divider()
        c1, c2, c3 = st.columns(3)
        c1.info("**Smart Extraction**\n\nAutomatically identifies Vendor, Date, and Line Items.")
        c2.warning("**Fraud Detection**\n\nFlags duplicate payments and unknown vendors.")
        c3.success("**QuickBooks Ready**\n\nOne-click export to your accounting software.")


# -----------------------------------------------------------------------------
# Workspace Area (Split View)
# -----------------------------------------------------------------------------
    else:
        result = st.session_state.processing_result
        file_obj = st.session_state.current_file
        
        # Top Bar: Actions
        act_col1, act_col2 = st.columns([6, 1])
        with act_col1:
            st.markdown(f"### 📄 Reviewing: `{file_obj.name}`")
        with act_col2:
            if st.button("New Upload"):
                reset_state()
                st.rerun()
                
        st.divider()

        # Split View Layout
        left_col, right_col = st.columns([1, 1], gap="large")
        
        # --- LEFT: Document Viewer ---
        with left_col:
            st.markdown("#### Source Document")
            if file_obj.type == "application/pdf":
                # Simple PDF embedding for browser
                # Note: For production, consider using streamlit-pdf-viewer
                import base64
                base64_pdf = base64.b64encode(file_obj.getvalue()).decode('utf-8')
                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800" type="application/pdf"></iframe>'
                st.markdown(pdf_display, unsafe_allow_html=True)
            elif file_obj.type.startswith("image"):
                st.image(file_obj, use_container_width=True)
            else:
                st.info("Preview not available for this file type (e.g. Docx). Viewing extracted text only.")

        # --- RIGHT: Data Workspace ---
        with right_col:
            st.markdown("#### Extracted Data")
            
            # Safely access extracted data (handle new/old claude formats)
            extracted = result.get("extraction_results", result.get("extracted_data", {}))
            
            # 1. Key Metrics Cards
            m1, m2, m3 = st.columns(3)
            
            # Helper to get value
            def get_val(key, default="--"):
                item = extracted.get(key, {})
                if isinstance(item, dict):
                    return item.get("value", default)
                return item if item else default

            vendor_name = get_val("vendor_name", "Unknown")
            inv_date = get_val("invoice_date", "N/A")
            total_amt = get_val("total_amount", 0)
            
            m1.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Vendor</div>
                <div class="metric-value">{vendor_name}</div>
            </div>
            """, unsafe_allow_html=True)
            
            m2.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Date</div>
                <div class="metric-value">{inv_date}</div>
            </div>
            """, unsafe_allow_html=True)
            
            try:
                val = float(total_amt)
                fmt_total = f"{val:,.2f}"
            except (ValueError, TypeError):
                fmt_total = "0.00"

            m3.markdown(f"""
            <div class="metric-container">
                <div class="metric-label">Total</div>
                <div class="metric-value">${fmt_total}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.write("") # Spacer

            # 2. Validation & Anomalies Logic
            validations = result.get("validation_results", result.get("validations", {}))
            if not isinstance(validations, dict):
                 validations = {}
            
            anomalies = result.get("anomalies", [])
            
            # Helper to safely get nested validation
            def get_val_status(key):
                v = validations.get(key, {})
                if isinstance(v, dict):
                    return v.get("valid", True)
                return True # Default to valid if malformed

            if anomalies or not get_val_status("vendor_validation"):
                with st.expander("⚠️ Validation Issues Detected", expanded=True):
                    if not get_val_status("vendor_validation"):
                         v_val = validations.get('vendor_validation', {})
                         msg = v_val.get('message') if isinstance(v_val, dict) else str(v_val)
                         st.warning(f"Vendor Issue: {msg}")
                    
                    for a in anomalies:
                        st.error(f"{a.get('type')}: {a.get('description')}")
            else:
                 st.success("✅ All Validations Passed")

            # 3. Line Items Editor
            st.markdown("##### Line Items")
            
            lines = extracted.get("line_items", [])
            # Flatten for editor
            flat_lines = []
            for item in lines:
                flat_lines.append({
                    "Description": item.get("description", ""),
                    "Qty": item.get("quantity", 0),
                    "Price": item.get("unit_price", 0.0),
                    "Total": item.get("total", 0.0)
                })
                
            if flat_lines:
                df_lines = pd.DataFrame(flat_lines)
                edited_df = st.data_editor(
                    df_lines,
                    num_rows="dynamic",
                    use_container_width=True
                )
                
                # Recalculate total from editor (visual only for now)
                try:
                    new_total = edited_df["Total"].sum()
                    if abs(new_total - float(total_amt)) > 0.01:
                        st.info(f"Calculated Total from lines: ${new_total:,.2f}")
                except Exception:
                    pass
            else:
                st.info("No line items extracted.")

            st.divider()
            
            # 4. Action Bar
            ac1, ac2 = st.columns(2)
            with ac1:
                active_erp_key = st.session_state.get("active_erp")
                manager = st.session_state.get(active_erp_key) if active_erp_key else None
                
                if manager and manager.is_connected():
                    # Determine ERP Name for label
                    erp_label = "ERP"
                    if isinstance(manager, QuickBooksManager): erp_label = "QuickBooks"
                    elif isinstance(manager, XeroManager): erp_label = "Xero"
                    elif isinstance(manager, NetSuiteManager): erp_label = "NetSuite"

                    if st.button(f"📤 Export to {erp_label}", type="primary", use_container_width=True):
                        try:
                            msg = manager.create_bill(extracted)
                            st.balloons()
                            st.toast(msg, icon="✅")
                        except Exception as e:
                            st.error(f"Export Error: {e}")
                else:
                     st.button("Export to ERP", disabled=True, use_container_width=True, help="Connect an ERP in Settings")
            
            with ac2:
                st.download_button(
                    "📥 Download JSON",
                    data=json.dumps(result, indent=2),
                    file_name="invoice_data.json",
                    mime="application/json",
                    use_container_width=True
                )
