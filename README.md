# Invoice Processing Agent - Enterprise Demo v2.0

## Overview

**Invoice Processing Agent** is an agentic AI system that currently automates the entire Accounts Payable (AP) lifecycle. It goes beyond simple data extraction to perform autonomous 2-way and 3-way matching, discrepancy resolution, and smart payment optimization.

### What It Does

- **Extracts** data from PDFs, Images, and Word Docs.
- **Validates** against an internal database of Vendors and Purchase Orders (POs).
- **Performs 3-Way Matching**: Matches Invoice vs. PO vs. Goods Receipts.
- **Optimizes Cash Flow**: Analyzes payment terms (e.g., "2/10 Net 30") to recommend the optimal payment date for capturing discounts.
- **Resolves Discrepancies**: Simulates autonomous outreach to vendors or self-correction for minor tolerance issues.
- **Visualizes Analytics**: Full spend analytics, invoice history, and optimization dashboards.

### Key Features (New in v2.0)

✅ **Autonomous 3-Way Matching** - Validates line items against received goods.  
✅ **Smart Payment Optimizer** - Calculates APR of early payment discounts to maximize savings.  
✅ **Goods Receipt Management** - UI for warehouse teams to log received inventory.  
✅ **Self-Correction & Outreach** - Agent can auto-correct small errors or draft vendor emails.  
✅ **Enhanced UI** - Metrics, tooltips, and dedicated dashboards for Vendors and Optimization.  

---

## Quick Start (5 minutes)

### 1. Clone/Setup

```bash
git clone https://github.com/your-repo/invoice_processor.git
cd invoice_processor
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
# Ensure Poppler (for PDF) is installed and in PATH
```

### 3. Configure API Key

Create a `.env` file:

```bash
ANTHROPIC_API_KEY=sk-ant-...
INVOICE_MODEL=claude-opus-4-1-20250805
```

### 4. Run the Web App

```bash
streamlit run app.py
```

Open <http://localhost:8501>.

---

## Workflows & Capabilities

### 1. Procurement & Receiving

- **Create POs**: Use the **Purchase Orders** tab to generate new POs.
- **Receive Goods**: Log incoming shipments against a PO. This creates `GoodsReceipt` records essential for 3-way matching.

### 2. Autonomous Processing

- **Upload**: Drop an invoice in the **Dashboard**.
- **Agent Logic**:
    1. **Extracts** terms and data.
    2. **Validates** vendor existence.
    3. **Matches**: Checks if `Invoice Amount == PO Amount` (2-way) and if `Invoice Amount <= Goods Received` (3-way).
    4. **Optimizes**: Checks for "2/10 Net 30" style terms.
    5. **Output**: Returns a JSON result with a recommendation (Approve, Pay Early, Flag).

### 3. Smart Payment Optimization

- The system identifies invoices with Early Payment Discounts.
- It calculates an effective APR for the discount.
- **Logic**: If `APR > 10% (Hurdle Rate)`, it suggests paying early.
- **Dashboard**: View the **Optimization** tab to see "Potential Savings" and cash flow forecasts.

### 4. Autonomous Outreach (Simulated)

- If a discrepancy is found (e.g. missing receipt), the agent simulates sending an email (`outreach_sent`) to the vendor.
- Can be configured to send real emails via SMTP (see configuration below).

---

## Configuration

### Autonomous Outreach

To enable real email sending for outreach actions, add these to `.env`:

```bash
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@example.com
SMTP_PASSWORD=your_password
```

### Database

The app uses a local SQLite database (`invoice_app.db`) to simulate an ERP environment.

**Models:**

- **Vendor**: Stores validated vendors, addresses, and `default_payment_terms`.
- **PurchaseOrder**: Tracks expected amounts, tolerances, and `GoodsReceipt` history.
- **Invoice**: Persists extracted invoice data, including `payment_terms`, `optimal_payment_date`, and `potential_savings`.
- **GoodsReceipt**: Records actual items received for 3-way matching.

**Integration:**

- The agent interacts with the DB via SQLAlchemy ORM.
- **Validation**: Agent queries `Vendor` table to validate incoming names.
- **Persistence**: Approved invoices are automatically saved to the `Invoice` table with full extraction results.

---

## Architecture

```
┌─────────────────────┐       ┌──────────────────────────────┐
│ Streamlit Frontend  │ <---> │      Invoice Agent (Backend) │
│ (Dash, POs, Opt)    │       │     (Claude Opus + Tools)    │
└──────────┬──────────┘       └──────────────┬───────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────┐       ┌──────────────────────────────┐
│  SQLite Database    │       │        Agent Tools           │
│ (Vendors, POs, Inv) │ <---- │ • validate_vendor            │
└─────────────────────┘       │ • perform_3_way_match        │
                              │ • optimize_payment           │
                              │ • resolve_discrepancy        │
                              └──────────────────────────────┘
```

---

## Feature Roadmap Status

| Feature | Status |
| :--- | :--- |
| **Data Extraction** | ✅ Live |
| **Vendor Validation** | ✅ Live |
| **Database Integration** | ✅ Live |
| **2-Way Matching** | ✅ Live |
| **3-Way Matching** | ✅ Live v2.0 |
| **Payment Optimization** | ✅ Live v2.0 |
| **Autonomous Outreach** | ✅ Live (Simulated) |
| **ERP Connectors (SAP/Oracle)** | 🚧 Planned |
| **Multi-Currency** | 🚧 Planned |

---

## Troubleshooting

- **Database Errors**: Delete `invoice_app.db` and restart `app.py` to re-seed fresh data.
- **PDF Errors**: Ensure `poppler-utils` is installed.
- **Optimization Not Working**: Ensure the Vendor has "Default Terms" set or the invoice contains clear terms like "Net 30".

---

**Zillion Technologies** - Enterprise InvoiceAI v2.0
