# Agent - Z (Strategic Intelligence Edition v3.0)

## Overview

**Agent - Z** is an enterprise-grade AI system that transforms Accounts Payable from a back-office function into a strategic asset.

It combines **Agentic AI** with **Strategic Intelligence** to automate the entire lifecycle—from zero-click ingestion to ERP export—while providing real-time financial insights via natural language chat.

### 🚀 Key Capabilities (v3.0)

#### 1. Zero-Click Automation

* **Automated Ingestion**: Monitors `inbox/` folder for new files.
* **Auto-Processing**: Instantly extracts, matches, and validates invoices without human intervention.
* **Smart Routing**: Moves files to `processed/` or `failed/` automatically.

#### 2. Strategic Intelligence

* **Agentic Spend QA**: A "Chat with Data" interface. Ask questions like *"Who is our top vendor?"* or *"What is our total spend on software?"*.
* **Smart Payment Optimization**: Calculates APR of early payment terms (e.g., "2/10 Net 30") and recommends optimal payment dates to maximize savings.

#### 3. Advanced Validation

* **3-Way Matching**: Validates `Invoice` vs `PO` vs `Goods Receipt` to prevent overpayment.
* **Self-Correction**: Autonomously resolves minor discrepancies or drafts vendor outreach emails.

#### 4. Enterprise Integration

* **Multi-ERP Support**: Native connectors for **QuickBooks Online**, **Xero**, and **NetSuite**.
* **Unified Interface**: Switch between ERPs dynamically in the settings.
* **Mock Mode**: Test all integrations safely without production credentials.

---

## Quick Start (5 minutes)

### 1. Setup

```bash
git clone https://github.com/your-repo/invoice_processor.git
cd invoice_processor
pip install -r requirements.txt
# Ensure Poppler (for PDF) is installed
```

### 2. Configure Environment

Create `.env`:

```bash
ANTHROPIC_API_KEY=sk-ant-...
INVOICE_MODEL=claude-3-opus-20240229
SMTP_SERVER=smtp.gmail.com  # Optional (for outreach)
```

### 3. Run the App

```bash
# Start the Web UI
streamlit run app.py

# (Optional) Start the Ingestion Service in a separate terminal
python ingestion_service.py
```

---

## Feature Deep Dive

### 🧠 Agentic Spend QA (Chat)

Located in the **AI Assistant** tab.

* **Natural Language SQL**: Converts English questions into secure database queries.
* **Context Aware**: Remembers your previous questions for a conversational experience.
* **Safety**: Uses a read-only connection to ensure data integrity.

### 🔌 ERP Connectors

Integrate with major ERP systems via the **Settings** sidebar.

**Configuration:**

1. Select **ERP System** (QuickBooks, Xero, NetSuite).
2. Enter credentials.
3. **Mock Mode**: Enter `mock` in credential fields to simulate a connection for testing.

**Workflow:**

* Connect to ERP.
* Process an invoice.
* Click **Export to [ERP Name]** to create a Bill/VendorBill automatically.

### 📥 Automated Ingestion

The background service `ingestion_service.py` enables "Touchless AP".

* **Watch Folder**: `./inbox`
* **Actions**:
  * Detect new file -> Run AI Agent -> Validate -> Save to DB -> Move to `./processed`.
  * On Failure -> Move to `./failed`.

---

## Architecture

```text
┌─────────────────────┐       ┌──────────────────────────────┐
│  Streamlit Web UI   │ <---> │      Invoice Agent (Core)    │
│ (Dash, Chat, ERP)   │       │     (Claude Opus + Tools)    │
└──────────┬──────────┘       └──────────────┬───────────────┘
           │                                 │
           ▼                                 ▼
┌─────────────────────┐       ┌──────────────────────────────┐
│  SQLite Database    │       │        Agent Tools           │
│ (Vendors, POs, Inv) │ <---- │ • validate_vendor            │
└─────────────────────┘       │ • perform_3_way_match        │
                              │ • optimize_payment           │
                              │ • resolve_discrepancy        │
                              └──────────────┬───────────────┘
                                             │
                                             ▼
                                  ┌──────────────────────┐
                                  │    ERP Connectors    │
                                  │ (QB, Xero, NetSuite) │
                                  └──────────────────────┘
```

---

## Feature Roadmap Status

| Feature | Status |
| :--- | :--- |
| **Data Extraction** | ✅ Live |
| **Vendor Validation** | ✅ Live |
| **3-Way Matching** | ✅ Live v2.0 |
| **Payment Optimization** | ✅ Live v2.0 |
| **Autonomous Outreach** | ✅ Live (Simulated) |
| **Automated Ingestion** | ✅ Live v3.0 |
| **Agentic Spend QA** | ✅ Live v3.0 |
| **ERP Connectors (QB/Xero/NetSuite)** | ✅ Live v3.0 |
| **Multi-Currency** | 🚧 Planned |

---

**Zillion Technologies** - *Thought beyond the DOT*
