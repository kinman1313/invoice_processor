import os
import time
from typing import Dict, Any

class NetSuiteManager:
    """
    Manager for Oracle NetSuite Integration.
    Supports 'Mock Mode' for testing without live credentials.
    """
    def __init__(self, account_id: str, consumer_key: str, consumer_secret: str, token_id: str, token_secret: str, mock_mode: bool = False):
        self.mock_mode = mock_mode
        self.account_id = account_id
        self.connected = False
        
        if self.mock_mode:
            self.connected = False # Will simulate connection in connect()
        
    def connect(self) -> bool:
        """Test connection to NetSuite"""
        if self.mock_mode:
            time.sleep(1)
            self.connected = True
            return True
            
        # Real implementation would call a sanitized endpoint (e.g. GET /server/time)
        return False
        
    def is_connected(self) -> bool:
        return self.connected

    def create_bill(self, invoice_data: Dict[str, Any]) -> str:
        """Create a Vendor Bill in NetSuite"""
        if not self.is_connected():
            raise RuntimeError("Not connected to NetSuite")

        vendor_name = invoice_data.get("vendor_name", {}).get("value", "Unknown Vendor")
        total_amount = invoice_data.get("total_amount", {}).get("value", 0)
        
        if self.mock_mode:
            time.sleep(1.5) # Simulate slower SOAP/REST response
            return f"NetSuite VendorBill Created (Mock) | Vendor: {vendor_name} | Amt: {total_amount} | InternalID: NS-{int(time.time())}"
            
        raise NotImplementedError("Real NetSuite API calls not implemented. Use Mock Mode.")
