import sys
import time
import os
import shutil
import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from invoice_agent import process_invoice

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Directories
INBOX_DIR = Path("inbox")
PROCESSED_DIR = Path("processed")
FAILED_DIR = Path("failed")

# Ensure directories exist
for d in [INBOX_DIR, PROCESSED_DIR, FAILED_DIR]:
    d.mkdir(exist_ok=True)

class InvoiceHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
            
        file_path = Path(event.src_path)
        
        # Ignored extensions
        if file_path.suffix.lower() not in ['.pdf', '.png', '.jpg', '.jpeg', '.docx', '.doc']:
            return
            
        # Ignore temp files
        if file_path.name.startswith("~$") or file_path.name.endswith(".tmp"):
            return

        logger.info(f"New file detected: {file_path}")
        
        # Wait briefly for file write to complete
        time.sleep(1)
        
        self.process_file(file_path)

    def process_file(self, file_path: Path):
        try:
            logger.info(f"Processing invoice: {file_path.name}...")
            
            # CALL THE AGENT
            result = process_invoice(str(file_path))
            
            if result.get("success"):
                destination = PROCESSED_DIR / file_path.name
                shutil.move(str(file_path), str(destination))
                logger.info(f"✅ Success! Moved to {destination}")
                
                # Retrieve extracted info for notification
                data = result.get("extracted_data", {})
                vendor = data.get("vendor_name", "Unknown")
                amount = data.get("total_amount", 0.0)
                
                print(f"\n[SLACK BOT] 🔔 New Invoice Processed:")
                print(f"   > Vendor: {vendor}")
                print(f"   > Amount: ${amount:,.2f}")
                print(f"   > Status: Auto-Approved ✅\n")
                
            else:
                raise Exception(result.get("error", "Unknown processing error"))
                
        except Exception as e:
            logger.error(f"❌ Failed to process {file_path.name}: {e}")
            
            # Encapsulate move in try/catch to avoid crash if file locked
            try:
                dest = FAILED_DIR / file_path.name
                shutil.move(str(file_path), str(dest))
                logger.info(f"Moved to {dest}")
                
                print(f"\n[SLACK BOT] ⚠️ Invoice Failed: {file_path.name}")
                print(f"   > Error: {str(e)}\n")
            except Exception as move_error:
                logger.error(f"Critical: Could not move failed file: {move_error}")

def start_watcher():
    event_handler = InvoiceHandler()
    observer = Observer()
    observer.schedule(event_handler, str(INBOX_DIR), recursive=False)
    observer.start()
    
    logger.info(f"👀 Watching directory: {INBOX_DIR.absolute()}")
    logger.info("Drop an invoice here to auto-process it.")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()

if __name__ == "__main__":
    start_watcher()
