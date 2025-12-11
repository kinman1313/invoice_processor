
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
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, environment: str = 'sandbox', mock_mode: bool = False):
        self.mock_mode = mock_mode
        if self.mock_mode:
            self.client = "MOCK_CLIENT"
        else:
            self.auth_client = AuthClient(
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                environment=environment,
            )
            self.client = None
        
    def get_auth_url(self) -> str:
        """Generate OAuth authorization URL"""
        if self.mock_mode:
            return "https://mock-auth-url.com"
        return self.auth_client.get_authorization_url([Scopes.ACCOUNTING])
        
    def handle_callback(self, auth_code: str, realm_id: str) -> None:
        """Exchange auth code for tokens and initialize client"""
        if self.mock_mode:
            self.client = "MOCK_CONNECTED"
            return

        self.auth_client.get_bearer_token(auth_code, realm_id=realm_id)
        self.client = QuickBooks(
            auth_client=self.auth_client,
            refresh_token=self.auth_client.refresh_token,
            company_id=realm_id,
            environment=self.auth_client.environment,
        )
        
    def is_connected(self) -> bool:
        return self.client is not None

    def _get_or_create_vendor(self, vendor_name: str) -> Any:
        """Find vendor by display name or create a new one"""
        if self.mock_mode:
            # Return a simple mock object with a to_ref method
            class MockVendor:
                def to_ref(self): return {"value": "123", "name": vendor_name}
            return MockVendor()

        vendors = Vendor.filter(DisplayName=vendor_name, qb=self.client)
        if vendors:
            return vendors[0]
        
        # Create new vendor
        new_vendor = Vendor()
        new_vendor.DisplayName = vendor_name
        new_vendor.save(qb=self.client)
        return new_vendor

    def _get_default_expense_account(self) -> Any:
        """Get a default expense account (usually ID 1 or first Expense account)"""
        if self.mock_mode:
             class MockAccount:
                def to_ref(self): return {"value": "99", "name": "Mock Expense"}
             return MockAccount()

        # Simplification: Try to find an account named "Purchases" or "Expense"
        # In prod, this should be configurable
        accounts = Account.filter(AccountType="Expense", qb=self.client)
        if accounts:
            return accounts[0]
        
        # Fallback to creating simple expense query if filter fails or none found
        # (For now just raising logic error if user has NO accounts)
        raise ValueError("No expense account found in QuickBooks. Please create one.")

    def create_bill(self, invoice_data: Dict[str, Any]) -> str:
        """Create a Bill in QuickBooks from invoice data"""
        if not self.is_connected():
            raise RuntimeError("Not connected to QuickBooks")

        # Extract data
        vendor_name = invoice_data.get("vendor_name", {}).get("value", "Unknown Vendor")
        total_amount = invoice_data.get("total_amount", {}).get("value", 0)
        
        # 1. Get/Create Vendor
        vendor = self._get_or_create_vendor(vendor_name)
        
        # 2. Prepare Line Items
        account = self._get_default_expense_account()
        
        if self.mock_mode:
             return f"Simulated Bill Created for {vendor_name} ($ {total_amount}). Mock ID: BILL-999"

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
