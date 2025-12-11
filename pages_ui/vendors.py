
import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Vendor

def render_vendors_page():
    st.title("👥 Vendor Management")
    
    db = SessionLocal()
    try:
        # 1. Add New Vendor
        with st.expander("➕ Add New Vendor", expanded=False):
            with st.form("add_vendor_form"):
                col1, col2 = st.columns(2)
                v_name = col1.text_input("Vendor Name (e.g. Acme Corp)")
                v_id = col2.text_input("Vendor ID (e.g. V001)")
                v_cat = col1.selectbox("Category", ["supplies", "software", "hardware", "utilities", "services", "other"])
                v_addr = col2.text_input("Address (Optional)")
                
                submitted = st.form_submit_button("Create Vendor")
                if submitted:
                    if v_name and v_id:
                        # Check duplicate
                        if db.query(Vendor).filter((Vendor.vendor_id == v_id) | (Vendor.name == v_name)).first():
                            st.error("Vendor with this ID or Name already exists.")
                        else:
                            new_vendor = Vendor(
                                vendor_id=v_id,
                                name=v_name,
                                category=v_cat,
                                address=v_addr
                            )
                            db.add(new_vendor)
                            db.commit()
                            st.success(f"Vendor '{v_name}' created!")
                            st.rerun()
                    else:
                        st.error("Name and ID are required.")

        st.divider()

        # 2. List Vendors
        st.subheader("Existing Vendors")
        
        vendors = db.query(Vendor).all()
        if vendors:
            data = [{
                "ID": v.id,
                "Vendor ID": v.vendor_id, 
                "Name": v.name, 
                "Category": v.category,
                "Address": v.address
            } for v in vendors]
            
            df = pd.DataFrame(data)
            
            # Editable Grid
            edited_df = st.data_editor(
                df,
                hide_index=True,
                column_config={
                    "ID": st.column_config.NumberColumn(disabled=True),
                    "Vendor ID": st.column_config.TextColumn(disabled=True),
                },
                key="vendor_editor"
            )
            # Note: Actual update logic for edited_df would go here in a real app
            # For prototype, we just display. To implement update, we'd compare df and edited_df
            
        else:
            st.info("No vendors found.")
            
    finally:
        db.close()
