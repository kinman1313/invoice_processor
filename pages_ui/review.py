import streamlit as st
import pandas as pd
import json
from database import SessionLocal
from models import Invoice, Vendor
from invoice_agent import perform_3_way_match, calculate_optimal_payment

def render():
    st.title("Human-in-the-Loop Workbench 🛠️")
    st.markdown("Review and correct **Flagged** invoices before they are exported.")

    db = SessionLocal()
    
    # 1. Fetch Flagged Invoices
    flagged = db.query(Invoice).filter(Invoice.status.in_(["flagged", "review"])).all()
    
    if not flagged:
        st.success("🎉 No invoices pending review!")
        db.close()
        return

    # Select Invoice
    options = {f"{inv.id}: {inv.vendor.name if inv.vendor else 'Unknown'} - ${inv.total_amount}": inv for inv in flagged}
    selected_label = st.selectbox("Select Invoice to Review", list(options.keys()))
    invoice = options[selected_label]
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("📝 Edit Data")
        
        # Load extracted data
        data = invoice.extracted_data or {}
        
        # Form for editing
        with st.form("edit_invoice_form"):
            # Vendor
            vendor_name = st.text_input("Vendor Name", value=invoice.vendor.name if invoice.vendor else "")
            
            # Details
            c1, c2 = st.columns(2)
            inv_num = c1.text_input("Invoice #", value=invoice.invoice_number or "")
            inv_date = c2.text_input("Date", value=invoice.date or "")
            
            # Financials
            c3, c4 = st.columns(2)
            amount = c3.number_input("Total Amount", value=float(invoice.total_amount), format="%.2f")
            po_num = c4.text_input("PO Number", value=data.get("po_number", {}).get("value", "") if isinstance(data.get("po_number"), dict) else str(data.get("po_number", "")))
            
            submitted = st.form_submit_button("Update & Re-Validate")
            
            if submitted:
                # Update Object
                invoice.invoice_number = inv_num
                invoice.date = inv_date
                invoice.total_amount = amount
                
                # Update JSON data wrapper (for re-validation logic)
                # We need to mimic the extract structure for the tools to work
                # Simplification: specific fields
                if "po_number" not in data or isinstance(data["po_number"], str):
                     data["po_number"] = {"value": po_num}
                else:
                     data["po_number"]["value"] = po_num
                     
                if "total_amount" not in data or isinstance(data["total_amount"], float):
                     data["total_amount"] = {"value": amount}
                else:
                     data["total_amount"]["value"] = amount

                invoice.extracted_data = data
                
                # 1. Re-run 3-Way Match
                # We need to construct a robust input for the matcher
                # The matcher expects: invoice_amount, po_number
                match_result = perform_3_way_match(amount, po_num)
                
                if "Discrepancy" in match_result or "Error" in match_result:
                    st.toast(match_result, icon="⚠️")
                    # Keep flagged
                else:
                    st.toast(match_result, icon="✅")
                    # If valid, Optimize and Approve
                    opt_res = calculate_optimal_payment(
                        data.get("payment_terms", {}).get("value", "Net 30"),
                        inv_date,
                        amount
                    )
                    
                    # Save Optimization
                    try:
                        # calculate_optimal_payment returns a dict, not string
                        invoice.payment_terms = opt_res.get("payment_terms")
                        invoice.optimal_payment_date = opt_res.get("optimal_payment_date")
                        invoice.potential_savings = opt_res.get("potential_savings", 0.0)
                    except:
                        pass
                        
                    invoice.status = "approved"
                    st.success("Invoice Approved!")
                
                db.commit()
                st.rerun()

    with col_right:
        st.subheader("⚠️ Issues")
        st.info("Original Extraction Data Below")
        st.json(invoice.extracted_data)
        
        st.divider()
        st.subheader("Actions")
        
        if st.button("Force Approve", type="primary"):
            invoice.status = "approved"
            db.commit()
            st.success("Force Approved!")
            st.rerun()
            
        if st.button("Reject Invoice"):
            invoice.status = "rejected"
            db.commit()
            st.warning("Invoice Rejected.")
            st.rerun()
            
    db.close()
