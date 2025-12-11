
from sqlalchemy import Column, Integer, String, Float, ForeignKey, JSON, DateTime, Boolean
from sqlalchemy.orm import relationship
from database import Base
from datetime import datetime

class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(String, unique=True, index=True) # e.g. "V001"

    name = Column(String, index=True)
    aliases = Column(JSON, default=[]) # List of auto-detected names
    category = Column(String)
    address = Column(String, nullable=True)
    default_payment_terms = Column(String, nullable=True) # e.g. "Net 30"
    
    purchase_orders = relationship("PurchaseOrder", back_populates="vendor")
    invoices = relationship("Invoice", back_populates="vendor")

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    po_number = Column(String, unique=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"))
    expected_amount = Column(Float)
    tolerance = Column(Float, default=0.1) # 10%
    status = Column(String, default="active") # active, closed
    
    vendor = relationship("Vendor", back_populates="purchase_orders")
    receipts = relationship("GoodsReceipt", back_populates="purchase_order")

class GoodsReceipt(Base):
    __tablename__ = "goods_receipts"

    id = Column(Integer, primary_key=True, index=True)
    po_id = Column(Integer, ForeignKey("purchase_orders.id"))
    receipt_number = Column(String, unique=True, index=True)
    received_date = Column(String) # ISO Format YYYY-MM-DD
    quantity = Column(Float, nullable=True)
    amount = Column(Float) # Value of goods received
    created_at = Column(DateTime, default=datetime.utcnow)
    
    purchase_order = relationship("PurchaseOrder", back_populates="receipts")

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    vendor_id = Column(Integer, ForeignKey("vendors.id"), nullable=True)
    invoice_number = Column(String, nullable=True)
    date = Column(String, nullable=True)
    total_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="processed") # processed, flagged, approved
    
    # Payment Optimization Fields
    payment_terms = Column(String, nullable=True)
    due_date = Column(String, nullable=True)
    discount_date = Column(String, nullable=True)
    optimal_payment_date = Column(String, nullable=True)
    potential_savings = Column(Float, default=0.0)
    
    extracted_data = Column(JSON) # Full raw JSON result
    
    vendor = relationship("Vendor", back_populates="invoices")
    lines = relationship("InvoiceLine", back_populates="invoice")

class InvoiceLine(Base):
    __tablename__ = "invoice_lines"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"))
    description = Column(String)
    quantity = Column(Float, nullable=True)
    unit_price = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    
    invoice = relationship("Invoice", back_populates="lines")
