"""
Generate sample test invoices for the invoice processor demo
Creates realistic invoice images for testing different scenarios
"""

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib import colors
from datetime import datetime, timedelta
import random
from pathlib import Path

def create_sample_invoices():
    """Create a set of sample invoices for testing"""
    
    samples_dir = Path("sample_invoices")
    samples_dir.mkdir(exist_ok=True)
    
    # Invoice 1: Clean, standard invoice
    create_invoice(
        filename="sample_invoices/invoice_clean.pdf",
        vendor_name="ACME Corp",
        invoice_number="INV-2024-1001",
        invoice_date="2024-01-15",
        po_number="PO-2024-001",
        line_items=[
            {"description": "Office Supplies Bundle", "qty": 5, "unit_price": 500, "total": 2500},
            {"description": "Delivery", "qty": 1, "unit_price": 2500, "total": 2500},
        ],
        total_amount=5000,
        invoice_type="clean"
    )
    
    # Invoice 2: Missing PO number
    create_invoice(
        filename="sample_invoices/invoice_missing_data.pdf",
        vendor_name="Tech Solutions Inc",
        invoice_number="TS-8374",
        invoice_date="2024-01-18",
        po_number=None,  # Missing PO
        line_items=[
            {"description": "Software License (Annual)", "qty": 1, "unit_price": 15000, "total": 15000},
        ],
        total_amount=15000,
        invoice_type="missing_po"
    )
    
    # Invoice 3: Amount mismatch with PO
    create_invoice(
        filename="sample_invoices/invoice_amount_mismatch.pdf",
        vendor_name="Office Depot",
        invoice_number="OD-92847",
        invoice_date="2024-01-20",
        po_number="PO-2024-003",
        line_items=[
            {"description": "Office Supplies", "qty": 2, "unit_price": 1500, "total": 3000},
        ],
        total_amount=3000,  # PO expects 2500, this is 3000 (exceeds tolerance)
        invoice_type="amount_mismatch"
    )
    
    # Invoice 4: Unknown vendor
    create_invoice(
        filename="sample_invoices/invoice_unknown_vendor.pdf",
        vendor_name="Random Vendor LLC",
        invoice_number="RV-55621",
        invoice_date="2024-01-22",
        po_number="PO-2024-004",  # This PO is for AWS, not Unknown Vendor
        line_items=[
            {"description": "Consulting Services", "qty": 40, "unit_price": 200, "total": 8000},
        ],
        total_amount=8000,
        invoice_type="unknown_vendor"
    )
    
    # Invoice 5: Complex multi-line invoice
    create_invoice(
        filename="sample_invoices/invoice_complex.pdf",
        vendor_name="AWS",
        invoice_number="AWS-2024-001",
        invoice_date="2024-01-25",
        po_number="PO-2024-004",
        line_items=[
            {"description": "EC2 Instances (m5.xlarge, 730 hours)", "qty": 1, "unit_price": 4200, "total": 4200},
            {"description": "RDS Database (db.r5.xlarge, 730 hours)", "qty": 1, "unit_price": 3000, "total": 3000},
            {"description": "Data Transfer (5TB outbound)", "qty": 1, "unit_price": 1300, "total": 1300},
        ],
        total_amount=8500,
        invoice_type="complex"
    )
    
    print(f"✅ Generated 5 sample invoices in 'sample_invoices/' directory")
    print("\nSamples created:")
    print("1. invoice_clean.pdf - Standard, valid invoice")
    print("2. invoice_missing_data.pdf - Missing PO number")
    print("3. invoice_amount_mismatch.pdf - Amount exceeds PO tolerance")
    print("4. invoice_unknown_vendor.pdf - Vendor not in database")
    print("5. invoice_complex.pdf - Multi-line cloud services invoice")


def create_invoice(filename, vendor_name, invoice_number, invoice_date, po_number, 
                   line_items, total_amount, invoice_type="standard"):
    """Create a sample invoice PDF"""
    
    # Create PDF
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#667eea'),
        spaceAfter=30,
        alignment=0
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        textColor=colors.HexColor('#333333'),
        spaceAfter=6
    )
    
    # Header
    story.append(Paragraph("INVOICE", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Invoice info table
    info_data = [
        ["Invoice #:", invoice_number, "Date:", invoice_date],
        ["Vendor:", vendor_name, "PO #:", po_number or "(Not provided)"],
    ]
    
    info_table = Table(info_data, colWidths=[1.5*inch, 2*inch, 1.5*inch, 2*inch])
    info_table.setStyle(TableStyle([
        ('FONT', (0, 0), (-1, -1), 'Helvetica', 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#667eea')),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    
    story.append(info_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Line items
    story.append(Paragraph("Line Items", heading_style))
    
    items_data = [['Description', 'Qty', 'Unit Price', 'Total']]
    for item in line_items:
        items_data.append([
            item['description'],
            str(item['qty']),
            f"${item['unit_price']:,.2f}",
            f"${item['total']:,.2f}"
        ])
    
    items_table = Table(items_data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.beige),
        ('FONT', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.lightgrey])
    ]))
    
    story.append(items_table)
    story.append(Spacer(1, 0.2*inch))
    
    # Total
    total_data = [
        ['', '', 'Subtotal:', f'${total_amount:,.2f}'],
        ['', '', 'Tax (0%):', '$0.00'],
        ['', '', 'TOTAL:', f'${total_amount:,.2f}'],
    ]
    
    total_table = Table(total_data, colWidths=[3.5*inch, 1*inch, 1.5*inch, 1.5*inch])
    total_table.setStyle(TableStyle([
        ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
        ('FONTNAME', (2, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (2, -1), (-1, -1), 14),
        ('BACKGROUND', (2, -1), (-1, -1), colors.HexColor('#667eea')),
        ('TEXTCOLOR', (2, -1), (-1, -1), colors.whitesmoke),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    
    story.append(total_table)
    story.append(Spacer(1, 0.3*inch))
    
    # Footer
    footer_text = f"Invoice Type: {invoice_type} | Generated for testing"
    story.append(Paragraph(footer_text, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    print(f"✅ Created {filename}")


if __name__ == "__main__":
    create_sample_invoices()
