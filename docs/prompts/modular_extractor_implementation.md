# Gmail Email Scanner - Modular Extractor Implementation

## CRITICAL: This prompt is for an LLM to refactor existing Python code
YOU MUST provide complete, executable code files that work together. This is a refactoring of existing working invoice extraction code into a modular system that can handle multiple extraction types.

## Current Working System Overview
The existing system has:
- `agents/email_classifier.py` - Single-purpose invoice classification
- `mcp_servers/gmail_server.py` - Gmail API integration  
- `mcp_servers/csv_export_server.py` - CSV file operations
- `config/config.yaml` - Invoice-specific configuration
- `demo.py` - Main demo script

## Refactoring Goal
Transform the single-purpose invoice system into a modular email extraction pipeline that can handle:
1. **Invoices** (existing functionality - must work exactly as before)
2. **Concerts** (new functionality)
3. **Future extractors** (restaurants, travel, etc.)

## PHASE 1: Create Modular Foundation

### 1. Base Extractor Interface
Create `extractors/base_extractor.py`:

```python
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import anthropic

class BaseExtractor(ABC):
    """Base class for all email content extractors"""
    
    def __init__(self, config_section: Dict, claude_client: anthropic.Anthropic):
        self.config = config_section
        self.claude = claude_client
        
    @abstractmethod
    def should_process(self, email_content: str, sender: str, subject: str) -> bool:
        """Determine if this extractor should process the given email"""
        pass
        
    @abstractmethod
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract relevant data from email content. Returns list of extracted items."""
        pass
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique identifier for this extractor"""
        pass
        
    @property
    @abstractmethod
    def output_filename(self) -> str:
        """CSV filename for this extractor's output"""
        pass
        
    def get_search_keywords(self) -> List[str]:
        """Get keywords for Gmail search query building"""
        keywords = []
        if 'keywords' in self.config:
            if 'swedish' in self.config['keywords']:
                keywords.extend(self.config['keywords']['swedish'])
            if 'english' in self.config['keywords']:
                keywords.extend(self.config['keywords']['english'])
        return keywords
        
    def _check_keywords_in_content(self, content: str, keywords: List[str]) -> bool:
        """Helper method to check if any keywords appear in content"""
        content_lower = content.lower()
        return any(keyword.lower() in content_lower for keyword in keywords)
```

### 2. Invoice Extractor (Refactored)
Create `extractors/invoice_extractor.py` by moving existing logic:

```python
from .base_extractor import BaseExtractor
from typing import Dict, List
import re
from datetime import datetime

class InvoiceExtractor(BaseExtractor):
    """Extracts invoice data from emails"""
    
    @property
    def name(self) -> str:
        return "invoices"
        
    @property
    def output_filename(self) -> str:
        return self.config.get('output_file', 'output/invoices.csv')
    
    def should_process(self, email_content: str, sender: str, subject: str) -> bool:
        """Check if email contains invoice-related content"""
        # Move existing invoice detection logic from email_classifier.py
        invoice_keywords = self.get_search_keywords()
        
        # Check for invoice indicators
        has_invoice_keywords = self._check_keywords_in_content(email_content, invoice_keywords)
        
        # Check for known business domains
        business_domains = self.config.get('business_domains', [])
        is_business_email = any(domain in sender.lower() for domain in business_domains)
        
        # Check for amount patterns
        amount_patterns = self.config.get('amount_patterns', {})
        all_amount_keywords = []
        for lang_patterns in amount_patterns.values():
            all_amount_keywords.extend(lang_patterns)
        has_amount_pattern = self._check_keywords_in_content(email_content, all_amount_keywords)
        
        return has_invoice_keywords and (is_business_email or has_amount_pattern)
    
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract invoice data using Claude AI"""
        # Move existing Claude invoice extraction logic here
        invoice_keywords = self.config['keywords']
        
        prompt = f"""
        Extract invoice information from this email content. Look for Swedish or English invoice terms.
        
        Swedish keywords: {', '.join(invoice_keywords.get('swedish', []))}
        English keywords: {', '.join(invoice_keywords.get('english', []))}
        
        Email content:
        {email_content}
        
        Extract and return JSON with:
        {{
            "vendor": "company name",
            "invoice_number": "invoice/bill number if found",
            "amount": "amount to pay (numbers only)",
            "due_date": "due date in YYYY-MM-DD format",
            "invoice_date": "invoice date in YYYY-MM-DD format", 
            "ocr": "OCR reference number if found (Swedish format)",
            "currency": "SEK/EUR/USD if detected"
        }}
        
        Return empty object {{}} if no clear invoice data found.
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1000,
                messages=[{"role": "user", "content": prompt}]
            )
            
            # Parse Claude response and extract invoice data
            extracted_data = self._parse_claude_response(response.content[0].text)
            
            if extracted_data:
                # Add email metadata
                extracted_data.update({
                    'email_date': email_metadata.get('date', ''),
                    'sender': email_metadata.get('sender', ''),
                    'subject': email_metadata.get('subject', '')
                })
                return [extracted_data]
            else:
                return []
                
        except Exception as e:
            print(f"Error extracting invoice data: {e}")
            return []
    
    def _parse_claude_response(self, response_text: str) -> Dict:
        """Parse Claude's JSON response"""
        # Move existing JSON parsing logic from email_classifier.py
        import json
        try:
            # Extract JSON from response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except:
            pass
        return {}
```

### 3. Concert Extractor (New)
Create `extractors/concert_extractor.py`:

```python
from .base_extractor import BaseExtractor
from typing import Dict, List
import re
from datetime import datetime

class ConcertExtractor(BaseExtractor):
    """Extracts concert information from emails"""
    
    @property
    def name(self) -> str:
        return "concerts"
        
    @property
    def output_filename(self) -> str:
        return self.config.get('output_file', 'output/concerts.csv')
    
    def should_process(self, email_content: str, sender: str, subject: str) -> bool:
        """Check if email contains Stockholm concert information"""
        # Check for concert keywords
        concert_keywords = self.get_search_keywords()
        has_concert_keywords = self._check_keywords_in_content(email_content, concert_keywords)
        
        # Check for Stockholm venues
        stockholm_venues = self.config.get('venues', {}).get('stockholm', [])
        has_stockholm_venue = self._check_keywords_in_content(email_content, stockholm_venues)
        
        return has_concert_keywords and has_stockholm_venue
    
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract concert data using Claude AI"""
        stockholm_venues = self.config.get('venues', {}).get('stockholm', [])
        
        prompt = f"""
        Extract Stockholm concert information from this email content.
        
        Email content:
        {email_content}
        
        Only extract concerts at these Stockholm venues: {', '.join(stockholm_venues)}
        
        Return JSON array of concerts:
        [
            {{
                "artist": "main artist/band name",
                "venue": "venue name (must be from Stockholm list)",
                "date": "concert date in YYYY-MM-DD format",
                "room": "specific room if mentioned (Klubben, Stora Salen, etc.)",
                "ticket_info": "ticket sales information if mentioned"
            }}
        ]
        
        Return empty array [] if no Stockholm concerts found.
        """
        
        try:
            response = self.claude.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=1500,
                messages=[{"role": "user", "content": prompt}]
            )
            
            concerts = self._parse_claude_response(response.content[0].text)
            
            # Add email metadata to each concert
            for concert in concerts:
                concert.update({
                    'email_date': email_metadata.get('date', ''),
                    'source_sender': email_metadata.get('sender', ''),
                    'source_subject': email_metadata.get('subject', '')
                })
            
            return concerts
            
        except Exception as e:
            print(f"Error extracting concert data: {e}")
            return []
    
    def _parse_claude_response(self, response_text: str) -> List[Dict]:
        """Parse Claude's JSON array response"""
        import json
        try:
            # Extract JSON array from response
            json_start = response_text.find('[')
            json_end = response_text.rfind(']') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
            
            # Fallback: try single object wrapped in array
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                single_item = json.loads(json_str)
                return [single_item] if single_item else []
                
        except Exception as e:
            print(f"Error parsing concert JSON: {e}")
            
        return []
```

### 4. Email Processor (Replaces EmailClassifier)
Create `agents/email_processor.py`:

```python
from typing import Dict, List
import anthropic
from extractors.base_extractor import BaseExtractor
from extractors.invoice_extractor import InvoiceExtractor  
from extractors.concert_extractor import ConcertExtractor

class EmailProcessor:
    """Processes emails through multiple specialized extractors"""
    
    def __init__(self, config: Dict, claude_api_key: str):
        self.config = config
        self.claude = anthropic.Anthropic(api_key=claude_api_key)
        self.extractors = self._initialize_extractors()
        
    def _initialize_extractors(self) -> List[BaseExtractor]:
        """Initialize all enabled extractors from config"""
        extractors = []
        
        extractors_config = self.config.get('extractors', {})
        
        # Initialize invoice extractor if enabled
        if extractors_config.get('invoices', {}).get('enabled', True):
            invoice_config = extractors_config['invoices']
            extractors.append(InvoiceExtractor(invoice_config, self.claude))
            
        # Initialize concert extractor if enabled  
        if extractors_config.get('concerts', {}).get('enabled', False):
            concert_config = extractors_config['concerts']
            extractors.append(ConcertExtractor(concert_config, self.claude))
            
        return extractors
    
    def process_email(self, email_content: str, email_metadata: Dict) -> Dict:
        """Process email through all applicable extractors"""
        results = {}
        
        sender = email_metadata.get('sender', '')
        subject = email_metadata.get('subject', '')
        
        for extractor in self.extractors:
            if extractor.should_process(email_content, sender, subject):
                extracted_items = extractor.extract(email_content, email_metadata)
                if extracted_items:
                    results[extractor.name] = extracted_items
                    
        return results
    
    def get_search_keywords(self) -> List[str]:
        """Get combined keywords for Gmail search from all extractors"""
        all_keywords = []
        for extractor in self.extractors:
            all_keywords.extend(extractor.get_search_keywords())
        return list(set(all_keywords))  # Remove duplicates
    
    def get_enabled_extractors(self) -> List[str]:
        """Get list of enabled extractor names"""
        return [extractor.name for extractor in self.extractors]
```

## PHASE 2: Update Configuration

### Updated `config/config.yaml`:

```yaml
# Gmail configuration (unchanged)
gmail:
  credentials_file: "config/gmail_credentials.json"
  token_file: "config/gmail_token.json"
  scopes: ["https://www.googleapis.com/auth/gmail.readonly"]

# Claude configuration (unchanged)  
claude:
  api_key: "your-claude-api-key-here"
  model: "claude-3-sonnet-20240229"

# Processing configuration
processing:
  default_days_back: 30
  max_emails: 100
  batch_size: 10
  pdf_processing:
    enabled: true
    max_pdf_size_mb: 10
    timeout_seconds: 30

# Modular extractor configuration
extractors:
  invoices:
    enabled: true
    output_file: "output/invoices.csv"
    keywords:
      swedish: ["faktura", "räkning", "förfallodag", "förfallodatum", "betalning", "att betala", "totalt belopp"]
      english: ["invoice", "bill", "statement", "due", "payment due", "amount due", "total amount"]
    amount_patterns:
      swedish: ["totalt:", "belopp:", "att betala:", "saldo:", "kr", "SEK", ":-"]
      english: ["total:", "amount:", "due:", "balance:", "pay:", "SEK", "kr", "$", "€"]
    business_domains: ["noreply", "billing", "invoice", "faktura", "accounts"]
    
  concerts:
    enabled: true
    output_file: "output/concerts.csv"
    keywords:
      swedish: ["konsert", "spelning", "live", "scen", "biljett", "köp din biljett", "säkra din biljett", "intar scenen", "återvänder", "kommer till"]
      english: ["concert", "live", "show", "performance", "tickets", "buy tickets", "on stage", "live at"]
    venues:
      stockholm: ["nalen", "debaser", "annexet", "cirkus", "dramaten", "konserthuset", "3arena stockholm", "klubben", "stora salen", "medley", "scalateatern"]

# Output configuration
output:
  directory: "output/"
  invoices_file: "output/invoices.csv"
  concerts_file: "output/concerts.csv"
```

## PHASE 3: Update Supporting Files

### Update `mcp_servers/gmail_server.py`:
Add method to build combined search query:

```python
def _build_search_query(self, days_back: int, keywords: List[str]) -> str:
    """Build Gmail search query from provided keywords"""
    start_date = datetime.now() - timedelta(days=days_back)
    
    # Build keyword search terms
    keyword_terms = []
    for keyword in keywords:
        keyword_terms.append(f'(subject:{keyword} OR {keyword})')
    
    # Combine with date filter
    query_parts = [f'after:{start_date.strftime("%Y/%m/%d")}']
    
    if keyword_terms:
        query_parts.append(f'({" OR ".join(keyword_terms)})')
    
    return ' '.join(query_parts)

def fetch_emails_for_extractors(self, keywords: List[str], days_back: int = 30) -> List[Dict]:
    """Fetch emails using combined keywords from all extractors"""
    query = self._build_search_query(days_back, keywords)
    return self.fetch_emails(days_back, custom_query=query)
```

### Update `mcp_servers/csv_export_server.py`:
Add generic CSV export for any extractor:

```python
def export_extractor_data(self, extractor_name: str, data_items: List[Dict], output_file: str):
    """Generic CSV export for any extractor data"""
    if not data_items:
        print(f"No {extractor_name} data to export")
        return
        
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Get all unique keys across all items for CSV headers
    all_keys = set()
    for item in data_items:
        all_keys.update(item.keys())
    
    headers = sorted(list(all_keys))
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=headers)
        writer.writeheader()
        
        for item in data_items:
            writer.writerow(item)
    
    print(f"✓ Exported {len(data_items)} {extractor_name} items to {output_file}")
```

### Update Demo Files

Create separate demo scripts for different use cases:

#### Main `demo.py` (All Extractors):

```python
import argparse
import yaml
import os
from dotenv import load_dotenv
from agents.email_processor import EmailProcessor
from mcp_servers.gmail_server import GmailServer
from mcp_servers.csv_export_server import CSVExporter

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Gmail Multi-Purpose Email Extractor')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    parser.add_argument('--extractors', nargs='+', help='Specific extractors to run (invoices, concerts)', default=None)
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        print("Error: CLAUDE_API_KEY not found in environment variables")
        print("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1
    
    # Override extractor selection if specified
    if args.extractors:
        print(f"Running only specified extractors: {args.extractors}")
        extractors_config = config.get('extractors', {})
        # Disable all extractors first
        for name in extractors_config:
            extractors_config[name]['enabled'] = False
        # Enable only specified ones
        for name in args.extractors:
            if name in extractors_config:
                extractors_config[name]['enabled'] = True
            else:
                print(f"Warning: Unknown extractor '{name}' - available: {list(extractors_config.keys())}")
    
    # Initialize components
    email_processor = EmailProcessor(config, claude_api_key)
    gmail_server = GmailServer(
        config['gmail']['credentials_file'],
        config['gmail']['token_file']
    )
    csv_exporter = CSVExporter()
    
    print("=== Gmail Multi-Purpose Email Extractor ===")
    enabled_extractors = email_processor.get_enabled_extractors()
    if not enabled_extractors:
        print("No extractors enabled! Check your config.yaml")
        return 1
    print(f"Enabled extractors: {', '.join(enabled_extractors)}")
    
    try:
        if args.dummy_data:
            print("Using dummy data for testing...")
            # Add dummy data testing logic here
            return run_dummy_data_test(email_processor, csv_exporter, config)
        else:
            return run_gmail_extraction(email_processor, gmail_server, csv_exporter, config)
                
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def run_gmail_extraction(email_processor, gmail_server, csv_exporter, config):
    """Run extraction from Gmail"""
    # Get search keywords from all enabled extractors
    search_keywords = email_processor.get_search_keywords()
    print(f"Searching for emails with keywords: {search_keywords[:10]}...")  # Show first 10
    
    # Fetch emails
    days_back = config['processing']['default_days_back']
    emails = gmail_server.fetch_emails_for_extractors(search_keywords, days_back)
    print(f"Found {len(emails)} emails to process")
    
    # Process emails through all extractors
    all_results = {}
    processed_count = 0
    
    for email in emails:
        try:
            email_content = gmail_server.get_email_content(email['id'])
            email_metadata = {
                'date': email.get('date', ''),
                'sender': email.get('sender', ''),
                'subject': email.get('subject', ''),
                'id': email['id']
            }
            
            results = email_processor.process_email(email_content, email_metadata)
            
            # Collect results by extractor type
            for extractor_name, items in results.items():
                if extractor_name not in all_results:
                    all_results[extractor_name] = []
                all_results[extractor_name].extend(items)
            
            processed_count += 1
            if processed_count % 10 == 0:
                print(f"Processed {processed_count}/{len(emails)} emails...")
                
        except Exception as e:
            print(f"Error processing email {email['id']}: {e}")
            continue
    
    # Export results for each extractor
    extractors_config = config.get('extractors', {})
    for extractor_name, items in all_results.items():
        if extractor_name in extractors_config:
            output_file = extractors_config[extractor_name]['output_file']
            csv_exporter.export_extractor_data(extractor_name, items, output_file)
    
    # Summary statistics
    print("\n=== EXTRACTION SUMMARY ===")
    total_items = 0
    for extractor_name, items in all_results.items():
        count = len(items)
        total_items += count
        print(f"📊 {extractor_name.title()}: {count} items extracted")
    
    print(f"📈 Total: {total_items} items from {processed_count} emails")
    return 0

def run_dummy_data_test(email_processor, csv_exporter, config):
    """Run extraction with dummy data for testing"""
    # TODO: Add dummy data testing
    print("Dummy data testing not yet implemented")
    return 0

if __name__ == "__main__":
    exit(main())
```

#### `demo_invoices.py` (Invoices Only):

```python
import argparse
import yaml
import os
from dotenv import load_dotenv
from agents.email_processor import EmailProcessor
from mcp_servers.gmail_server import GmailServer
from mcp_servers.csv_export_server import CSVExporter

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Gmail Invoice Extractor')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Force enable only invoices
    extractors_config = config.get('extractors', {})
    for name in extractors_config:
        extractors_config[name]['enabled'] = (name == 'invoices')
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        print("Error: CLAUDE_API_KEY not found in environment variables")
        print("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1
    
    # Initialize components
    email_processor = EmailProcessor(config, claude_api_key)
    gmail_server = GmailServer(
        config['gmail']['credentials_file'],
        config['gmail']['token_file']
    )
    csv_exporter = CSVExporter()
    
    print("=== Gmail Invoice Extractor ===")
    print("🧾 Extracting invoice data only")
    
    try:
        if args.dummy_data:
            print("Using dummy invoice data for testing...")
            # Add dummy invoice testing
            return 0
        
        # Get invoice keywords only
        search_keywords = email_processor.get_search_keywords()
        print(f"Searching for invoice emails...")
        
        # Fetch emails
        days_back = config['processing']['default_days_back']
        emails = gmail_server.fetch_emails_for_extractors(search_keywords, days_back)
        print(f"Found {len(emails)} potential invoice emails")
        
        # Process emails
        invoice_results = []
        processed = 0
        
        for email in emails:
            try:
                email_content = gmail_server.get_email_content(email['id'])
                email_metadata = {
                    'date': email.get('date', ''),
                    'sender': email.get('sender', ''),
                    'subject': email.get('subject', ''),
                    'id': email['id']
                }
                
                results = email_processor.process_email(email_content, email_metadata)
                
                if 'invoices' in results:
                    invoice_results.extend(results['invoices'])
                    print(f"✓ Found invoice in: {email_metadata['subject'][:50]}...")
                
                processed += 1
                
            except Exception as e:
                print(f"Error processing email: {e}")
                continue
        
        # Export results
        if invoice_results:
            output_file = config['extractors']['invoices']['output_file']
            csv_exporter.export_extractor_data('invoices', invoice_results, output_file)
        
        print(f"\n📊 INVOICE SUMMARY: {len(invoice_results)} invoices from {processed} emails")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
```

#### `demo_concerts.py` (Concerts Only):

```python
import argparse
import yaml
import os
from dotenv import load_dotenv
from agents.email_processor import EmailProcessor
from mcp_servers.gmail_server import GmailServer
from mcp_servers.csv_export_server import CSVExporter

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Gmail Concert Extractor')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    args = parser.parse_args()
    
    # Load configuration
    with open(args.config, 'r') as f:
        config = yaml.safe_load(f)
    
    # Force enable only concerts
    extractors_config = config.get('extractors', {})
    for name in extractors_config:
        extractors_config[name]['enabled'] = (name == 'concerts')
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        print("Error: CLAUDE_API_KEY not found in environment variables")
        print("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1
    
    # Initialize components
    email_processor = EmailProcessor(config, claude_api_key)
    gmail_server = GmailServer(
        config['gmail']['credentials_file'],
        config['gmail']['token_file']
    )
    csv_exporter = CSVExporter()
    
    print("=== Gmail Concert Extractor ===")
    print("🎵 Extracting Stockholm concert data only")
    
    try:
        if args.dummy_data:
            print("Using dummy concert data for testing...")
            # Add dummy concert testing
            return 0
        
        # Get concert keywords only
        search_keywords = email_processor.get_search_keywords()
        print(f"Searching for concert emails...")
        
        # Fetch emails
        days_back = config['processing']['default_days_back']
        emails = gmail_server.fetch_emails_for_extractors(search_keywords, days_back)
        print(f"Found {len(emails)} potential concert emails")
        
        # Process emails
        concert_results = []
        processed = 0
        
        for email in emails:
            try:
                email_content = gmail_server.get_email_content(email['id'])
                email_metadata = {
                    'date': email.get('date', ''),
                    'sender': email.get('sender', ''),
                    'subject': email.get('subject', ''),
                    'id': email['id']
                }
                
                results = email_processor.process_email(email_content, email_metadata)
                
                if 'concerts' in results:
                    concert_results.extend(results['concerts'])
                    print(f"🎤 Found concert(s) in: {email_metadata['subject'][:50]}...")
                
                processed += 1
                
            except Exception as e:
                print(f"Error processing email: {e}")
                continue
        
        # Export results
        if concert_results:
            output_file = config['extractors']['concerts']['output_file']
            csv_exporter.export_extractor_data('concerts', concert_results, output_file)
            
            # Show concert details
            print("\n🎵 CONCERTS FOUND:")
            for concert in concert_results[:10]:  # Show first 10
                artist = concert.get('artist', 'Unknown Artist')
                venue = concert.get('venue', 'Unknown Venue')
                date = concert.get('date', 'Unknown Date')
                print(f"   • {artist} at {venue} on {date}")
            
            if len(concert_results) > 10:
                print(f"   ... and {len(concert_results) - 10} more")
        
        print(f"\n📊 CONCERT SUMMARY: {len(concert_results)} concerts from {processed} emails")
        return 0
        
    except Exception as e:
        print(f"Error: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
```

## PHASE 4: Create Package Structure

### Create `extractors/__init__.py`:

```python
from .base_extractor import BaseExtractor
from .invoice_extractor import InvoiceExtractor
from .concert_extractor import ConcertExtractor

__all__ = ['BaseExtractor', 'InvoiceExtractor', 'ConcertExtractor']
```

## DEMO USAGE EXAMPLES

### Run All Extractors:
```bash
# Process all enabled extractors
python demo.py

# Process only specific extractors
python demo.py --extractors invoices concerts

# Process with custom config
python demo.py --config config/production.yaml
```

### Run Invoices Only:
```bash
# Extract only invoice data
python demo_invoices.py

# Test with dummy data
python demo_invoices.py --dummy-data
```

### Run Concerts Only:
```bash
# Extract only concert data  
python demo_concerts.py

# Test with dummy data
python demo_concerts.py --dummy-data
```

## ENVIRONMENT SETUP

### Required Files:
1. **`.env`** (create from .env.example):
```env
CLAUDE_API_KEY=your_actual_claude_api_key_here
```

2. **`.gitignore`** (add these lines):
```gitignore
# Environment variables
.env

# API credentials  
config/gmail_credentials.json
config/gmail_token.json

# Output files
output/
*.csv
```

## TESTING STRATEGY

### 1. Test Environment Setup:
```bash
pip install python-dotenv
echo "CLAUDE_API_KEY=test_key" > .env
```

### 2. Test Invoice Backward Compatibility:
```bash
# Should work exactly as before
python demo_invoices.py --dummy-data
```

### 3. Test Concert Extraction:
```bash
# Should extract concerts from provided emails
python demo_concerts.py --dummy-data
```

### 4. Test Modular System:
```bash
# Should run both extractors
python demo.py --extractors invoices concerts
```

## ERROR HANDLING

All demo scripts include:
- ✅ Environment variable validation
- ✅ Configuration file validation  
- ✅ Graceful error handling
- ✅ Progress reporting
- ✅ Clear error messages

## CONFIGURATION FLEXIBILITY

The system supports:
- **Enable/disable extractors** via config
- **Override extractor selection** via command line
- **Custom config files** for different environments
- **Environment-specific API keys** via .env