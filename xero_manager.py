import os
import time
from typing import Dict, Any

class XeroManager:
    """
    Manager for Xero Integration.
    Supports 'Mock Mode' for testing without live credentials.
    """
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.client = None
        
        if self.mock_mode:
            self.client = "MOCK_XERO_CLIENT"
        
    def get_auth_url(self) -> str:
        """Generate OAuth authorization URL"""
        if self.mock_mode:
            return "https://login.xero.com/identity/connect/authorize?response_type=code&client_id=mock&redirect_uri=mock&scope=accounting.transactions"
        
        # Real implementation would use requests_oauthlib setup
        return f"https://login.xero.com/identity/connect/authorize?response_type=code&client_id={self.client_id}&redirect_uri={self.redirect_uri}"
        
    def handle_callback(self, auth_code: str) -> None:
        """Exchange auth code for tokens and initialize client"""
        if self.mock_mode:
            self.client = "MOCK_XERO_CONNECTED"
            return
            
        # Real implementation would swap code for token
        raise NotImplementedError("Real Xero Auth not fully implemented. Please use Mock Mode.")
        
    def is_connected(self) -> bool:
        return self.client is not None

    def create_bill(self, invoice_data: Dict[str, Any]) -> str:
        """Create a Bill (Invoice) in Xero"""
        if not self.is_connected():
            raise RuntimeError("Not connected to Xero")

        vendor_name = invoice_data.get("vendor_name", {}).get("value", "Unknown Vendor")
        total_amount = invoice_data.get("total_amount", {}).get("value", 0)
        
        if self.mock_mode:
            time.sleep(1) # Simulate network lag
            return f"Xero Bill Created (Mock) for {vendor_name} ({total_amount}). ID: X-BILL-{int(time.time())}"
            
        # Real implementation would post to https://api.xero.com/api.xro/2.0/Invoices
        raise NotImplementedError("Real Xero API calls not implemented. Use Mock Mode.")
