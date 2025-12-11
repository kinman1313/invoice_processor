
import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Vendor, PurchaseOrder

def render_pos_page():
    st.title("📦 Purchase Order Management")
    
    db = SessionLocal()
    try:
        # 1. Add New PO
        with st.expander("➕ Add New Purchase Order", expanded=False):
            with st.form("add_po_form"):
                col1, col2 = st.columns(2)
                
                # Vendor Selection
                vendors = db.query(Vendor).all()
                vendor_options = {f"{v.name} ({v.vendor_id})": v.id for v in vendors}
                
                po_num = col1.text_input("PO Number (e.g. PO-2024-001)")
                vendor_selection = col2.selectbox("Vendor", options=list(vendor_options.keys()) if vendors else [])
                
                amount = col1.number_input("Expected Amount ($)", min_value=0.0, step=0.01)
                tolerance = col2.number_input("Tolerance (0.0 - 1.0)", min_value=0.0, max_value=1.0, value=0.1, step=0.01)
                
                submitted = st.form_submit_button("Create PO")
                
                if submitted:
                    if not vendors:
                        st.error("No vendors found. Please create a vendor first.")
                    elif not po_num:
                        st.error("PO Number is required.")
                    else:
                        selected_vendor_id = vendor_options[vendor_selection]
                        
                        # Check duplicate
                        if db.query(PurchaseOrder).filter_by(po_number=po_num).first():
                            st.error(f"PO Number '{po_num}' already exists.")
                        else:
                            new_po = PurchaseOrder(
                                po_number=po_num,
                                vendor_id=selected_vendor_id,
                                expected_amount=amount,
                                tolerance=tolerance
                            )
                            db.add(new_po)
                            db.commit()
                            st.success(f"Purchase Order '{po_num}' created!")
                            st.rerun()

        st.divider()

        # 2. List POs
        st.subheader("Active Purchase Orders")
        
        pos = db.query(PurchaseOrder).all()
        if pos:
            data = []
            for po in pos:
                v_name = po.vendor.name if po.vendor else "Unknown"
                data.append({
                    "ID": po.id,
                    "PO Number": po.po_number,
                    "Vendor": v_name,
                    "Amount": f"${po.expected_amount:,.2f}",
                    "Tolerance": f"{po.tolerance*100:.0f}%",
                    "Status": po.status
                })
            
            df = pd.DataFrame(data)
            
            st.dataframe(
                df,
                hide_index=True,
                use_container_width=True
            )
            
        else:
            st.info("No purchase orders found.")
            
    finally:
        db.close()
