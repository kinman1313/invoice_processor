
import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Vendor, PurchaseOrder, GoodsReceipt

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

        # 2. Receive Goods (New)
        with st.expander("🚚 Receive Goods (3-Way Match)", expanded=False):
            st.caption("Record goods received against an active PO for 3-way matching validation.")
            
            # Get Active POs using a new query to ensure freshness
            active_pos = db.query(PurchaseOrder).filter(PurchaseOrder.status == 'active').all()
            po_options = {f"{po.po_number} - {po.vendor.name}": po.id for po in active_pos if po.vendor}
            
            with st.form("receive_goods_form"):
                r_col1, r_col2 = st.columns(2)
                
                selected_po_key = r_col1.selectbox("Select PO", options=list(po_options.keys()) if active_pos else [])
                receipt_num = r_col2.text_input("Receipt Number / Delivery Note")
                
                r_col3, r_col4 = st.columns(2)
                
                rec_date = r_col3.date_input("Date Received")
                rec_amount = r_col4.number_input("Value of Goods Received ($)", min_value=0.0, step=0.01)
                
                rec_submitted = st.form_submit_button("Record Receipt")
                
                if rec_submitted:
                    if not active_pos:
                        st.error("No active POs found.")
                    elif not receipt_num:
                        st.error("Receipt Number is required.")
                    else:
                        po_id = po_options[selected_po_key]
                        
                        # Check duplicate receipt
                        if db.query(GoodsReceipt).filter_by(receipt_number=receipt_num).first():
                             st.error(f"Receipt '{receipt_num}' already exists.")
                        else:
                            new_receipt = GoodsReceipt(
                                po_id=po_id,
                                receipt_number=receipt_num,
                                received_date=str(rec_date),
                                amount=rec_amount
                            )
                            db.add(new_receipt)
                            db.commit()
                            st.success(f"Receipt '{receipt_num}' recorded against PO!")
                            st.rerun()

        st.divider()

        # 3. List POs & Receipts
        st.subheader("Active Purchase Orders & Receipts")
        
        pos = db.query(PurchaseOrder).all()
        if pos:
            for po in pos:
                with st.container():
                    # Calculate total received
                    total_received = sum(r.amount for r in po.receipts)
                    match_pct = (total_received / po.expected_amount * 100) if po.expected_amount > 0 else 0
                    
                    st.markdown(f"**{po.po_number}** | {po.vendor.name if po.vendor else 'Unk'} | Exp: ${po.expected_amount:,.2f} | Rec: ${total_received:,.2f} ({match_pct:.0f}%)")
                    
                    # Show receipts if any
                    if po.receipts:
                        r_data = []
                        for r in po.receipts:
                            r_data.append({
                                "Receipt #": r.receipt_number,
                                "Date": r.received_date,
                                "Amount": f"${r.amount:,.2f}"
                            })
                        st.dataframe(pd.DataFrame(r_data), use_container_width=True, hide_index=True)
                    else:
                        st.caption("No goods received yet.")
                    
                    st.divider()
            
        else:
            st.info("No purchase orders found.")
            
    finally:
        db.close()
