
import os
from intuitlib.client import AuthClient
from intuitlib.enums import Scopes
from quickbooks import QuickBooks
from quickbooks.objects.bill import Bill, AccountBasedExpenseLine
from quickbooks.objects.detailline import AccountBasedExpenseLineDetail
from quickbooks.objects.vendor import Vendor
from quickbooks.objects.account import Account
from typing import Dict, Any, List, Optional
from datetime import datetime

class QuickBooksManager:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, environment: str = 'sandbox'):
        self.auth_client = AuthClient(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            environment=environment,
        )
        self.client = None
        
    def get_auth_url(self) -> str:
        """Generate OAuth authorization URL"""
        return self.auth_client.get_authorization_url([Scopes.ACCOUNTING])
        
    def handle_callback(self, auth_code: str, realm_id: str) -> None:
        """Exchange auth code for tokens and initialize client"""
        self.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=self.auth_client.refresh_token,
            company_id=realm_id,
            environment=self.auth_client.environment,
        )
        
    def is_connected(self) -> bool:
        return self.client is not None

    def _get_or_create_vendor(self, vendor_name: str) -> Vendor:
        """Find vendor by display name or create a new one"""
        vendors = Vendor.filter(DisplayName=vendor_name, qb=self.client)
        if vendors:
            return vendors[0]
        
        # Create new vendor
        new_vendor = Vendor()
        new_vendor.DisplayName = vendor_name
        new_vendor.save(qb=self.client)
        return new_vendor

    def _get_default_expense_account(self) -> Account:
        """Get a default expense account (usually ID 1 or first Expense account)"""
        # Simplification: Try to find an account named "Purchases" or "Expense"
        # In prod, this should be configurable
        accounts = Account.filter(AccountType="Expense", qb=self.client)
        if accounts:
            return accounts[0]
        raise ValueError("No expense account found in QuickBooks. Please create one.")

    def create_bill(self, invoice_data: Dict[str, Any]) -> str:
        """Create a Bill in QuickBooks from invoice data"""
        if not self.is_connected():
            raise RuntimeError("Not connected to QuickBooks")

        # Extract data
        vendor_name = invoice_data.get("vendor_name", {}).get("value", "Unknown Vendor")
        total_amount = invoice_data.get("total_amount", {}).get("value", 0)
        # Parse date or use today
        
        # 1. Get/Create Vendor
        vendor = self._get_or_create_vendor(vendor_name)
        
        # 2. Prepare Line Items
        # Simplification: Create one line item for the total amount
        # since mapping extracted lines to GL accounts is complex without user input
        account = self._get_default_expense_account()
        
        line_detail = AccountBasedExpenseLineDetail()
        line_detail.AccountRef = account.to_ref()
        
        line = AccountBasedExpenseLine()
        line.DetailType = "AccountBasedExpenseLineDetail"
        line.Amount = float(total_amount)
        line.AccountBasedExpenseLineDetail = line_detail
        
        # 3. Create Bill
        bill = Bill()
        bill.VendorRef = vendor.to_ref()
        bill.Line.append(line)
        bill.save(qb=self.client)
        
        return f"Bill created successfully. ID: {bill.Id}"
