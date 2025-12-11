
import streamlit as st
import pandas as pd
from database import SessionLocal
from models import Invoice, Vendor, PurchaseOrder
import datetime

def render_analytics_page():
    st.title("📊 Spend Analytics")
    
    db = SessionLocal()
    try:
        # Fetch Data
        invoices = db.query(Invoice).all()
        
        if not invoices:
            st.info("No data available for analytics. Process some invoices first.")
            return

        # Prepare DataFrames
        data = []
        for inv in invoices:
            v_name = inv.vendor.name if inv.vendor else "Unknown"
            data.append({
                "Date": inv.date, # String or date? Need to ensure datetime for charts
                "Amount": inv.total_amount,
                "Vendor": v_name,
                "Month": datetime.datetime.strptime(inv.date, "%Y-%m-%d").strftime("%Y-%m") if inv.date else "Unknown"
            })
            
        df = pd.DataFrame(data)
        
        # Ensure Date is datetime
        df["Date"] = pd.to_datetime(df["Date"], errors='coerce')
        if "Amount" not in df.columns:
            df["Amount"] = 0.0
            
        # 1. Top Level Metrics
        total_spend = df["Amount"].sum()
        total_invoices = len(df)
        unique_vendors = df["Vendor"].nunique()
        
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Spend (All Time)", f"${total_spend:,.2f}")
        m2.metric("Total Invoices", total_invoices)
        m3.metric("Active Vendors", unique_vendors)
        
        st.divider()
        
        # 2. Spend by Vendor (Bar Chart)
        st.subheader("Spend by Vendor")
        vendor_spend = df.groupby("Vendor")["Amount"].sum().sort_values(ascending=False).reset_index()
        st.bar_chart(vendor_spend, x="Vendor", y="Amount", use_container_width=True)
        
        # 3. Spend Over Time (Line Chart)
        st.subheader("Spend Over Time")
        time_spend = df.groupby("Date")["Amount"].sum().reset_index().sort_values("Date")
        st.line_chart(time_spend, x="Date", y="Amount", use_container_width=True)
        
        # 4. Recent Transactions
        st.subheader("Recent Transactions")
        st.dataframe(
            df.sort_values("Date", ascending=False).head(10)[["Date", "Vendor", "Amount"]],
            use_container_width=True,
            hide_index=True
        )

    except Exception as e:
        st.error(f"Error loading analytics: {e}")
    finally:
        db.close()
