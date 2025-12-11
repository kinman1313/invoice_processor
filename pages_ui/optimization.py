import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Invoice, Vendor
from datetime import datetime, timedelta

def render_optimization_page():
    st.title("💰 Smart Payment Optimization")
    st.caption("Maximize working capital and capture early payment discounts.")
    
    db = SessionLocal()
    try:
        # 1. Summary Metrics
        invoices = db.query(Invoice).filter(Invoice.status != 'paid').all()
        
        total_outstanding = sum(inv.total_amount for inv in invoices)
        potential_savings = sum(inv.potential_savings for inv in invoices if inv.potential_savings)
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Outstanding Payables", f"${total_outstanding:,.2f}", help="Sum of all unpaid processed invoices")
        m2.metric("Potential Savings Available", f"${potential_savings:,.2f}", delta="Capture Now", help="Total discount available if paid by 'Optimal Date'")
        m3.metric("Invoices to Review", len(invoices))
        
        st.divider()
        
        # 2. Savings Opportunities (Priority)
        st.subheader("🚀 High Priority: Discount Opportunities")
        
        # Filter for invoices with savings > 0
        opportunity_invs = [i for i in invoices if i.potential_savings and i.potential_savings > 0]
        
        if opportunity_invs:
            for inv in opportunity_invs:
                with st.expander(f"Invoice {inv.invoice_number} - Save ${inv.potential_savings:,.2f}", expanded=True):
                    c1, c2, c3 = st.columns(3)
                    c1.write(f"**Vendor:** {inv.vendor.name if inv.vendor else 'Unk'}")
                    c1.write(f"**Amount:** ${inv.total_amount:,.2f}")
                    
                    c2.write(f"**Terms:** {inv.payment_terms}")
                    c2.write(f"**Discount Date:** {inv.discount_date}")
                    
                    c3.success(f"**Recommendation:** Pay by {inv.optimal_payment_date}")
                    
                    if st.button(f"Pay Now (Save ${inv.potential_savings:.2f})", key=f"pay_{inv.id}"):
                        st.balloons()
                        st.success("Payment Scheduled!")
                        # In real app, update status to 'scheduled'
        else:
            st.info("No active discount opportunities found.")
            
        st.divider()
        
        # 3. Cash Flow Forecast (Calendar View style list)
        st.subheader("📅 Cash Flow Forecast")
        
        # Sort by optimal payment date
        sorted_invs = sorted(invoices, key=lambda x: x.optimal_payment_date or "9999-99-99")
        
        data = []
        for inv in sorted_invs:
            data.append({
                "Invoice #": inv.invoice_number,
                "Vendor": inv.vendor.name if inv.vendor else "Unknown",
                "Due Date": inv.due_date,
                "Optimal Date": inv.optimal_payment_date,
                "Amount": f"${inv.total_amount:,.2f}",
                "Action": "Take Discount" if (inv.potential_savings or 0) > 0 else "Pay Net"
            })
            
        if data:
            st.dataframe(
                pd.DataFrame(data),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No pending invoices.")
            
    finally:
        db.close()
