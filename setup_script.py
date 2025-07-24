#!/usr/bin/env python3
"""
Gmail Invoice Agent - Project Setup Script
Creates all necessary files and directories for the project
"""

import os
import sys

def create_directory_structure():
    """Create the project directory structure"""
    directories = [
        'config',
        'output',
        'tests',
        'tests/fixtures'
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}/")

def create_requirements_txt():
    """Create requirements.txt"""
    content = """anthropic>=0.25.0
google-auth>=2.22.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.100.0
pyyaml>=6.0
pandas>=2.0.0
python-dateutil>=2.8.0
tqdm>=4.65.0
pytest>=7.4.0
pytest-mock>=3.11.0
pytest-cov>=4.1.0
responses>=0.23.0"""
    
    with open('requirements.txt', 'w') as f:
        f.write(content)
    print("✓ Created requirements.txt")

def create_config_yaml():
    """Create config/config.yaml"""
    content = """# Gmail Invoice Agent Configuration
claude:
  api_key: "your-claude-api-key-here"
  model: "claude-3-5-sonnet-20241022"

gmail:
  credentials_file: "config/gmail_credentials.json"
  token_file: "config/gmail_token.json"
  scopes: ["https://www.googleapis.com/auth/gmail.readonly"]

processing:
  default_days_back: 30
  max_emails: 100
  batch_size: 10

# Invoice identification keywords (Swedish focus, English support)
invoice_keywords:
  invoice_indicators:
    swedish: ["faktura", "räkning", "förfallodag", "förfallodatum", "betalning", "att betala", "totalt belopp", "slutsumma", "ocr", "bankgiro", "plusgiro"]
    english: ["invoice", "bill", "statement", "due", "payment due", "amount due", "total amount", "balance due"]
  
  vendor_identifiers:
    swedish: ["från:", "faktura från", "räkning från", "avsändare:"]
    english: ["from:", "invoice from", "bill from", "statement from"]
    
  amount_patterns:
    swedish: ["totalt:", "belopp:", "att betala:", "saldo:", "kr", "SEK", ":-", "summa:", "slutsumma:"]
    english: ["total:", "amount:", "due:", "balance:", "pay:", "SEK", "kr", "$", "€"]
    
  date_patterns:
    swedish: ["förfallodag:", "förfallodatum:", "betalas senast:", "betala före:", "förfaller:"]
    english: ["due date:", "payment due:", "due by:", "pay by:", "expiry date:"]

# Common Swedish vendors for better recognition
common_vendors:
  swedish:
    - "Vattenfall"
    - "Telia"
    - "Telenor"
    - "ICA"
    - "Coop"
    - "Skatteverket"
    - "Försäkringskassan"
    - "CSN"
    - "Spotify"
    - "Nordea"
    - "SEB"
    - "Swedbank"
    - "Handelsbanken"
  english:
    - "PayPal"
    - "Amazon"
    - "Microsoft"
    - "Google"
    - "Adobe"

output:
  invoices_file: "output/invoices.csv"
  log_file: "output/processing.log"
"""
    
    with open('config/config.yaml', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Created config/config.yaml")

def create_gmail_server_py():
    """Create gmail_server.py"""
    content = '''import os
import base64
import email
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time

logger = logging.getLogger(__name__)

class GmailServer:
    def __init__(self, credentials_file: str, token_file: str, scopes: List[str]):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.service = None
        self._authenticate()
    
    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.warning(f"Token refresh failed: {e}. Getting new credentials.")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(f"Gmail credentials file not found: {self.credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
        
        self.service = build('gmail', 'v1', credentials=creds)
        logger.info("Gmail authentication successful")
    
    def fetch_emails(self, days_back: int = 30, max_emails: int = 100) -> List[Dict]:
        """Fetch emails from the last N days"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            # Gmail search query for potential invoices
            query = f'after:{start_date.strftime("%Y/%m/%d")} (subject:faktura OR subject:räkning OR subject:invoice OR subject:bill OR has:attachment filetype:pdf)'
            
            logger.info(f"Searching emails from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
            
            # Get message list
            results = self.service.users().messages().list(
                userId='me', 
                q=query,
                maxResults=max_emails
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f"Found {len(messages)} potential invoice emails")
            
            emails = []
            for i, message in enumerate(messages):
                try:
                    email_data = self._get_email_details(message['id'])
                    if email_data:
                        emails.append(email_data)
                        logger.info(f"Processed email {i+1}/{len(messages)}: {email_data['subject'][:50]}...")
                    
                    # Rate limiting - be nice to Gmail API
                    if i > 0 and i % 10 == 0:
                        time.sleep(1)
                        
                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(emails)} emails")
            return emails
            
        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []
    
    def _get_email_details(self, message_id: str) -> Optional[Dict]:
        """Get detailed information for a specific email"""
        try:
            message = self.service.users().messages().get(
                userId='me', 
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload'].get('headers', [])
            
            # Extract header information
            subject = self._get_header_value(headers, 'Subject') or 'No Subject'
            sender = self._get_header_value(headers, 'From') or 'Unknown Sender'
            date_header = self._get_header_value(headers, 'Date')
            
            # Parse date
            email_date = self._parse_email_date(date_header)
            
            # Get email body
            body = self._extract_email_body(message['payload'])
            
            # Get attachments info
            attachments = self._get_attachment_info(message['payload'])
            
            return {
                'id': message_id,
                'subject': subject,
                'sender': sender,
                'date': email_date,
                'body': body,
                'attachments': attachments,
                'raw_headers': headers
            }
            
        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None
    
    def _get_header_value(self, headers: List[Dict], name: str) -> Optional[str]:
        """Extract header value by name"""
        for header in headers:
            if header['name'].lower() == name.lower():
                return header['value']
        return None
    
    def _parse_email_date(self, date_string: str) -> Optional[str]:
        """Parse email date string to ISO format"""
        if not date_string:
            return None
        
        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(date_string)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return date_string
    
    def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body text from payload"""
        body = ""
        
        if 'parts' in payload:
            # Multipart message
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body += self._decode_base64(part['body']['data'])
                elif part['mimeType'] == 'text/html' and not body:
                    # Use HTML if no plain text found
                    if 'data' in part['body']:
                        body += self._decode_base64(part['body']['data'])
        else:
            # Single part message
            if payload['mimeType'] in ['text/plain', 'text/html']:
                if 'data' in payload['body']:
                    body += self._decode_base64(payload['body']['data'])
        
        return body.strip()
    
    def _decode_base64(self, data: str) -> str:
        """Decode base64 email content"""
        try:
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode('utf-8', errors='replace')
        except Exception as e:
            logger.warning(f"Error decoding base64 data: {e}")
            return ""
    
    def _get_attachment_info(self, payload: Dict) -> List[Dict]:
        """Get information about email attachments"""
        attachments = []
        
        if 'parts' in payload:
            for part in payload['parts']:
                filename = part.get('filename', '')
                if filename and part['body'].get('attachmentId'):
                    attachments.append({
                        'filename': filename,
                        'mimeType': part['mimeType'],
                        'size': part['body'].get('size', 0),
                        'attachmentId': part['body']['attachmentId']
                    })
        
        return attachments
'''
    
    with open('gmail_server.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("✓ Created gmail_server.py")

def print_next_steps():
    """Print setup completion message"""
    print("\n" + "="*60)
    print("🎉 Gmail Invoice Agent - Project Created Successfully!")
    print("="*60)
    print("\n📋 Next Steps:")
    print("1. Install dependencies:")
    print("   pip install -r requirements.txt")
    print("\n2. Configure your Claude API key:")
    print("   Edit config/config.yaml")
    print("   Replace 'your-claude-api-key-here' with your actual key")
    print("\n3. Setup Gmail API:")
    print("   - Go to Google Cloud Console")
    print("   - Download OAuth credentials JSON")
    print("   - Save as config/gmail_credentials.json")
    print("\n4. Test the setup:")
    print("   python test_basic.py")
    print("\n5. Run the demo:")
    print("   python demo.py --days-back 7 --verbose")
    print("\n📄 See setup_instructions.md for detailed setup guide")
    print("\n🚀 Happy invoice processing!")

def main():
    """Main setup function"""
    print("🚀 Creating Gmail Invoice Agent project structure...")
    print()
    
    # Create directories
    create_directory_structure()
    
    # Create core files
    create_requirements_txt()
    create_config_yaml()
    create_gmail_server_py()
    
    # Note: The other Python files are too large for this script
    # User should copy them from the provided artifacts
    
    print(f"\n⚠️  Note: Please copy the remaining files from the artifacts:")
    print("   - email_classifier.py")
    print("   - csv_exporter.py") 
    print("   - demo.py")
    print("   - test_basic.py")
    print("   - README.md")
    print("   - setup_instructions.md")
    
    print_next_steps()

if __name__ == "__main__":
    main()
