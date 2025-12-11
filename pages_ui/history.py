
import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Invoice, Vendor
import json

def render_history_page():
    st.title("📜 Invoice History")
    
    db = SessionLocal()
    try:
        # Fetch Invoices
        invoices = db.query(Invoice).order_by(Invoice.created_at.desc()).all()
        
        if invoices:
            data = []
            for inv in invoices:
                # Resolve Vendor Name
                v_name = "Unknown"
                if inv.vendor:
                    v_name = inv.vendor.name
                
                data.append({
                    "ID": inv.id,
                    "Date": inv.date,
                    "Vendor": v_name,
                    "Invoice #": inv.invoice_number,
                    "Amount": inv.total_amount,
                    "Status": inv.status,
                    "Created At": inv.created_at,
                    "Raw Data": inv.extracted_data
                })
            
            df = pd.DataFrame(data)
            
            # Formatting for display
            display_df = df.copy()
            display_df["Amount"] = display_df["Amount"].apply(lambda x: f"${x:,.2f}" if pd.notnull(x) else "$0.00")
            
            st.dataframe(
                display_df.drop(columns=["Raw Data"]),
                hide_index=True,
                use_container_width=True
            )
            
            st.divider()
            
            # JSON Inspector
            st.subheader("🔍 Inspect Details")
            selected_id = st.selectbox("Select Invoice ID to Inspect", options=df["ID"].tolist())
            
            if selected_id:
                row = df[df["ID"] == selected_id].iloc[0]
                st.json(row["Raw Data"])
                
        else:
            st.info("No invoice history found. Process some documents to see them here.")
            
    finally:
        db.close()
