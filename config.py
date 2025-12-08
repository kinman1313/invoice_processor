"""
Configuration file for Invoice Processing Agent
Customize vendors, PO rules, and validation thresholds
"""

# Model configuration
MODEL_CONFIG = {
    "model": "claude-opus-4-1-20250805",
    "max_tokens": 2048,
    "temperature": 0.3,  # Lower for deterministic results
}

# Vendor database - extend this with your vendors
VENDORS = {
    "acme corp": {
        "id": "V001",
        "category": "supplies",
        "status": "active",
        "terms": "net_30"
    },
    "tech solutions inc": {
        "id": "V002",
        "category": "software",
        "status": "active",
        "terms": "net_45"
    },
    "office depot": {
        "id": "V003",
        "category": "supplies",
        "status": "active",
        "terms": "net_30"
    },
    "aws": {
        "id": "V004",
        "category": "cloud services",
        "status": "active",
        "terms": "monthly"
    },
    "microsoft": {
        "id": "V005",
        "category": "software",
        "status": "active",
        "terms": "monthly"
    },
    "fedex": {
        "id": "V006",
        "category": "shipping",
        "status": "active",
        "terms": "net_15"
    },
    "usps": {
        "id": "V007",
        "category": "shipping",
        "status": "active",
        "terms": "monthly"
    },
    "ups": {
        "id": "V008",
        "category": "shipping",
        "status": "active",
        "terms": "net_15"
    },
    "dell": {
        "id": "V009",
        "category": "hardware",
        "status": "active",
        "terms": "net_30"
    },
    "hp": {
        "id": "V010",
        "category": "hardware",
        "status": "active",
        "terms": "net_30"
    },
    "cisco": {
        "id": "V011",
        "category": "networking",
        "status": "active",
        "terms": "net_45"
    },
    "salesforce": {
        "id": "V012",
        "category": "software",
        "status": "active",
        "terms": "monthly"
    },
    "slack": {
        "id": "V013",
        "category": "software",
        "status": "active",
        "terms": "monthly"
    },
    "stripe": {
        "id": "V014",
        "category": "payment processing",
        "status": "active",
        "terms": "monthly"
    },
    "twilio": {
        "id": "V015",
        "category": "communications",
        "status": "active",
        "terms": "monthly"
    },
}

# PO database - purchase orders with expected amounts
PO_RULES = {
    "PO-2024-001": {
        "vendor": "acme corp",
        "expected_amount": 5000,
        "tolerance_percent": 10,  # Allow ±10% variance
        "status": "active",
        "budget_owner": "ops"
    },
    "PO-2024-002": {
        "vendor": "tech solutions inc",
        "expected_amount": 15000,
        "tolerance_percent": 10,
        "status": "active",
        "budget_owner": "it"
    },
    "PO-2024-003": {
        "vendor": "office depot",
        "expected_amount": 2500,
        "tolerance_percent": 10,
        "status": "active",
        "budget_owner": "admin"
    },
    "PO-2024-004": {
        "vendor": "aws",
        "expected_amount": 8500,
        "tolerance_percent": 15,  # Cloud services get more tolerance
        "status": "active",
        "budget_owner": "infrastructure"
    },
}

# Validation rules and thresholds
VALIDATION_RULES = {
    "amount_thresholds": {
        "small": 1000,      # Under $1000 - low risk
        "medium": 5000,     # $1000-5000 - medium review
        "large": 10000,     # $10000+ - high review
        "critical": 50000   # $50000+ - executive review
    },
    "invoice_aging": {
        "standard": 30,     # Standard invoice is within 30 days
        "warning": 60,      # Invoice more than 60 days old - flag it
        "critical": 90      # Invoice more than 90 days old - critical
    },
    "confidence_thresholds": {
        "auto_approve": 0.95,      # Confidence > 95% - auto approve
        "manual_review": 0.80,     # Confidence 80-95% - needs review
        "reject": 0.80            # Confidence < 80% - reject/rework
    },
    "duplicate_detection": {
        "enabled": True,
        "days_back": 30,           # Check for duplicates in last 30 days
        "exact_match_threshold": 0.99,
        "fuzzy_match_threshold": 0.85
    }
}

# Anomaly detection rules
ANOMALY_RULES = {
    "missing_vendor": {
        "severity": "high",
        "message": "Vendor not found in database",
        "action": "review"
    },
    "vendor_mismatch": {
        "severity": "high",
        "message": "Vendor does not match PO vendor",
        "action": "review"
    },
    "amount_mismatch": {
        "severity": "high",
        "message": "Invoice amount outside PO tolerance",
        "action": "review"
    },
    "missing_po": {
        "severity": "medium",
        "message": "No PO number found on invoice",
        "action": "review"
    },
    "missing_invoice_number": {
        "severity": "medium",
        "message": "Invoice number not found",
        "action": "review"
    },
    "missing_amount": {
        "severity": "critical",
        "message": "Total amount not clearly visible",
        "action": "reject"
    },
    "stale_invoice": {
        "severity": "low",
        "message": "Invoice is older than 30 days",
        "action": "notify"
    },
    "unusually_high": {
        "severity": "medium",
        "message": "Invoice amount significantly higher than average for this vendor",
        "action": "review"
    },
    "unusually_low": {
        "severity": "low",
        "message": "Invoice amount significantly lower than average for this vendor",
        "action": "notify"
    }
}

# Approval workflow routing
APPROVAL_WORKFLOW = {
    "auto_approve": {
        "conditions": [
            "confidence > 95%",
            "all_validations_pass",
            "no_high_severity_anomalies",
            "amount < $5000"
        ],
        "approver": "system"
    },
    "manager_review": {
        "conditions": [
            "confidence >= 80%",
            "amount >= $5000 AND amount < $10000",
            "some_validations_fail"
        ],
        "approver": "manager"
    },
    "director_review": {
        "conditions": [
            "amount >= $10000 AND amount < $50000",
            "critical_anomalies"
        ],
        "approver": "director"
    },
    "executive_review": {
        "conditions": [
            "amount >= $50000",
            "multiple_critical_issues"
        ],
        "approver": "executive"
    },
    "reject": {
        "conditions": [
            "confidence < 80%",
            "missing_critical_fields",
            "fraud_indicators"
        ],
        "action": "return_to_vendor"
    }
}

# Integration settings
INTEGRATION_SETTINGS = {
    "erp_systems": {
        "sap": {
            "enabled": False,
            "endpoint": "https://your-sap.com/api",
            "credentials": "vault:sap_creds"
        },
        "oracle": {
            "enabled": False,
            "endpoint": "https://your-oracle.com/api",
            "credentials": "vault:oracle_creds"
        },
        "netsuite": {
            "enabled": False,
            "endpoint": "https://your-netsuite.com/api",
            "credentials": "vault:netsuite_creds"
        }
    },
    "notifications": {
        "email_approvals": True,
        "slack_alerts": False,
        "webhook_endpoints": []
    },
    "audit_logging": {
        "enabled": True,
        "log_level": "INFO",
        "retention_days": 365
    }
}

# Processing settings
PROCESSING_CONFIG = {
    "batch_size": 10,
    "timeout_seconds": 30,
    "retry_attempts": 3,
    "cache_enabled": True,
    "cache_ttl_hours": 24
}

# Compliance and security
COMPLIANCE_CONFIG = {
    "data_retention": {
        "invoices_days": 2555,      # 7 years
        "logs_days": 1825,          # 5 years
        "audit_trail_immutable": True
    },
    "pii_handling": {
        "mask_pii": True,
        "allowed_fields": ["vendor_name", "invoice_amount", "invoice_date"],
        "redacted_fields": ["bank_account", "tax_id", "employee_id"]
    },
    "compliance_frameworks": [
        "SOX",
        "GDPR",
        "HIPAA",
        "PCI-DSS"
    ]
}


def get_vendor_by_name(vendor_name: str) -> dict:
    """Get vendor configuration by name"""
    vendor_lower = vendor_name.lower().strip()
    return VENDORS.get(vendor_lower, None)


def get_po_rules(po_number: str) -> dict:
    """Get PO rules by PO number"""
    po_upper = po_number.strip().upper()
    return PO_RULES.get(po_upper, None)


def get_amount_category(amount: float) -> str:
    """Get risk category based on amount"""
    thresholds = VALIDATION_RULES["amount_thresholds"]
    if amount < thresholds["small"]:
        return "small"
    elif amount < thresholds["medium"]:
        return "medium"
    elif amount < thresholds["large"]:
        return "large"
    else:
        return "critical"


def get_approval_route(confidence: float, amount: float, has_issues: bool) -> str:
    """Determine approval route based on confidence, amount, and issues"""
    if has_issues:
        if confidence < 0.80 or amount >= 50000:
            return "executive_review"
        elif amount >= 10000:
            return "director_review"
        elif amount >= 5000:
            return "manager_review"
        else:
            return "manual_review"
    else:
        if confidence >= 0.95 and amount < 5000:
            return "auto_approve"
        elif amount >= 50000:
            return "executive_review"
        elif amount >= 10000:
            return "director_review"
        elif amount >= 5000:
            return "manager_review"
        else:
            return "auto_approve"


if __name__ == "__main__":
    # Test configuration
    print("Configuration loaded successfully")
    print(f"Vendors configured: {len(VENDORS)}")
    print(f"PO rules configured: {len(PO_RULES)}")
    print(f"Anomaly rules configured: {len(ANOMALY_RULES)}")
