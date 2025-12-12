import streamlit as st
from models import Invoice, Vendor
from database import SessionLocal
from streamlit_agraph import agraph, Node, Edge, Config

def render():
    st.title("🕸️ Supply Chain Nerve Center")
    st.markdown("Visualizing the relationships between your **Vendors** and **Invoices**. Flagged items appear in **Red**.")
    
    db = SessionLocal()
    
    try:
        vendors = db.query(Vendor).all()
        invoices = db.query(Invoice).all()
        
        nodes = []
        edges = []
        
        # 1. Vendor Nodes (Hubs)
        for v in vendors:
            # Calculate total spend per vendor for sizing
            vendor_spend = sum(inv.total_amount for inv in v.invoices) if v.invoices else 0
            size = 25 + (int(vendor_spend / 1000) * 5) # Base size + spend factor
            size = min(size, 60) # Cap size
            
            nodes.append(Node(
                id=v.vendor_id, 
                label=v.name, 
                size=size, 
                color="#0068C9", # Streamlit Blue
                shape="circularImage",
                image="https://img.icons8.com/color/48/company.png" # generic icon
            ))
            
        # 2. Invoice Nodes (Spokes)
        for inv in invoices:
            status_color = "#28a745" # Green
            if inv.status in ["flagged", "review", "rejected"]:
                status_color = "#dc3545" # Red
                
            node_id = f"INV-{inv.id}"
            label = f"${inv.total_amount:.0f}\n{inv.date}"
            
            nodes.append(Node(
                id=node_id,
                label=label,
                size=15,
                color=status_color,
                shape="dot"
            ))
            
            # 3. Edges (Links)
            if inv.vendor:
                edges.append(Edge(
                    source=inv.vendor.vendor_id,
                    target=node_id,
                    type="CURVE_SMOOTH"
                ))
            
        # 4. Configuration
        config = Config(
            width=1200,
            height=800,
            directed=True, 
            physics=True, 
            hierarchical=False,
            nodeHighlightBehavior=True, 
            highlightColor="#F7A7A6", # Light Red highlight
            collapsible=True
        )
        
        # 5. Render
        if not nodes:
            st.info("No data found to visualize.")
        else:
            return_value = agraph(nodes=nodes, edges=edges, config=config)
            
    finally:
        db.close()
