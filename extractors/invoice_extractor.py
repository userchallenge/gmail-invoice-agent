from .base_extractor import BaseExtractor
from typing import Dict, List
import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

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
        # Use existing invoice detection logic from email_classifier.py
        text_to_check = f"{subject} {sender}".lower()
        
        # Check for invoice indicators in subject and sender
        invoice_keywords = self.get_search_keywords()
        has_invoice_keywords = self._check_keywords_in_content(text_to_check, invoice_keywords)
        
        # Check for known business domains
        business_domains = self.config.get('business_domains', [])
        is_business_email = any(domain in sender.lower() for domain in business_domains)
        
        # Check for amount patterns in email content
        amount_patterns = self.config.get('amount_patterns', {})
        all_amount_keywords = []
        for lang_patterns in amount_patterns.values():
            all_amount_keywords.extend(lang_patterns)
        has_amount_pattern = self._check_keywords_in_content(email_content, all_amount_keywords)
        
        return has_invoice_keywords and (is_business_email or has_amount_pattern)
    
    def get_additional_search_filters(self) -> List[str]:
        """Get additional search filters for invoices (PDF attachments are common)"""
        return ["has:attachment filename:pdf"]
    
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract invoice data using Claude AI"""
        try:
            # Clean and prepare context for Claude (handle encoding issues)
            subject = self._clean_text(email_metadata.get('subject', ''))
            sender = self._clean_text(email_metadata.get('sender', ''))
            body = self._clean_text(email_content)[:2000]  # Limit body length
            
            # Include PDF content if available
            pdf_content = ""
            if email_metadata.get('pdf_processed') and email_metadata.get('pdf_text'):
                pdf_text = self._clean_text(email_metadata.get('pdf_text', ''))[:3000]  # Limit PDF text length
                pdf_filename = email_metadata.get('pdf_filename', 'unknown.pdf')
                pdf_content = f"""

--- PDF ATTACHMENT CONTENT ---
PDF File: {pdf_filename}
PDF Text:
{pdf_text}
--- END PDF CONTENT ---
"""
            
            email_content_formatted = f"""
Subject: {subject}
From: {sender}
Date: {email_metadata.get('date', '')}
Body: {body}

Attachments: {[self._clean_text(att.get('filename', '')) for att in email_metadata.get('attachments', [])]}
{pdf_content}
"""
            
            prompt = f"""You are an expert at identifying and extracting data from Swedish and English invoices in emails and PDF attachments.

Analyze this email (including any PDF attachment content) and determine:
1. Is this a legitimate invoice/bill (not promotional, not receipt, not notification)?
2. If yes, extract the following information:

Email Content:
{email_content_formatted}

Extract this information if it's an invoice:
- vendor: Company/organization name
- invoice_number: Invoice or reference number  
- amount: Total amount (just the number, no currency)
- currency: Currency (SEK, USD, EUR, etc.)
- due_date: Payment due date (YYYY-MM-DD format)
- invoice_date: Invoice date (YYYY-MM-DD format)
- ocr: OCR number (Swedish format, typically 16-20 digits)
- description: Brief description of what this is for

IMPORTANT: If PDF attachment content is provided (marked with "--- PDF ATTACHMENT CONTENT ---"), 
prioritize the PDF content over email text as PDFs often contain the actual invoice details.

Swedish Invoice Patterns to Look For:
- OCR numbers: Long numeric strings (16-20 digits)
- Keywords: faktura, räkning, förfallodag, att betala, totalt belopp
- Common vendors: Vattenfall, Telia, ICA, Skatteverket, etc.
- Currency: kr, SEK, :-

English Invoice Patterns:
- Keywords: invoice, bill, payment due, total amount
- Date formats: various international formats
- Currency: $, €, SEK, etc.

Respond with ONLY a JSON object like this:
{{
    "is_invoice": true/false,
    "vendor": "vendor name",
    "invoice_number": "invoice number",
    "amount": "amount without currency",
    "currency": "SEK/USD/EUR",
    "due_date": "YYYY-MM-DD",
    "invoice_date": "YYYY-MM-DD", 
    "ocr": "OCR number if found",
    "description": "brief description",
    "confidence": 0.0-1.0
}}

If not an invoice, respond with: {{"is_invoice": false}}"""
            
            # Use base class method for Claude API call
            response_text = self._call_claude(prompt, max_tokens=1000)
            if not response_text:
                return []
            
            # Parse Claude response using base class method
            extracted_data = self._parse_json_response(response_text, is_array=False)
            
            if extracted_data and extracted_data.get('is_invoice'):
                # Add email metadata
                extracted_data.update({
                    'email_date': email_metadata.get('date', ''),
                    'sender': email_metadata.get('sender', ''),
                    'subject': email_metadata.get('subject', ''),
                    'email_id': email_metadata.get('id', '')
                })
                
                # Format the data for CSV export
                formatted_data = self._format_invoice_data(extracted_data, email_metadata)
                logger.info(f"✓ Extracted invoice from {extracted_data.get('vendor', 'Unknown')}")
                return [formatted_data]
            else:
                logger.debug(f"Claude determined this is not an invoice: {email_metadata.get('subject', '')}")
                return []
                
        except Exception as e:
            logger.error(f"Error extracting invoice data: {e}")
            return []
    
    
    def _format_invoice_data(self, claude_data: Dict, email_metadata: Dict) -> Dict:
        """Format the extracted data for CSV export"""
        return {
            'email_id': email_metadata.get('id', ''),
            'email_subject': email_metadata.get('subject', ''),
            'email_sender': email_metadata.get('sender', ''),
            'email_date': email_metadata.get('date', ''),
            'vendor': (claude_data.get('vendor') or '').strip(),
            'invoice_number': (claude_data.get('invoice_number') or '').strip(),
            'amount': self._clean_amount(claude_data.get('amount', '')),
            'currency': claude_data.get('currency', 'SEK').upper(),
            'due_date': self._clean_date(claude_data.get('due_date', '')),
            'invoice_date': self._clean_date(claude_data.get('invoice_date', '')),
            'ocr': (claude_data.get('ocr') or '').strip(),
            'description': (claude_data.get('description') or '').strip(),
            'confidence': claude_data.get('confidence', 0.0),
            'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            # PDF processing metadata
            'pdf_processed': email_metadata.get('pdf_processed', False),
            'pdf_filename': email_metadata.get('pdf_filename', ''),
            'pdf_text_length': email_metadata.get('pdf_text_length', 0),
            'pdf_processing_error': email_metadata.get('pdf_processing_error', '')
        }
    
    def _clean_amount(self, amount_str: str) -> str:
        """Clean and normalize amount string"""
        if not amount_str:
            return ''
        
        # Remove common currency symbols and separators
        cleaned = re.sub(r'[kr$€£,:SEK\s]', '', str(amount_str))
        
        # Handle decimal separators (both . and ,)
        if '.' in cleaned and ',' in cleaned:
            # If both, assume . is thousands separator and , is decimal
            cleaned = cleaned.replace('.', '').replace(',', '.')
        elif ',' in cleaned and len(cleaned.split(',')[-1]) == 2:
            # If comma with 2 digits after, it's decimal separator
            cleaned = cleaned.replace(',', '.')
        
        # Keep only digits and one decimal point
        try:
            float_val = float(cleaned)
            return str(float_val)
        except ValueError:
            logger.warning(f"Could not parse amount: {amount_str}")
            return amount_str
    
    def _clean_date(self, date_str: str) -> str:
        """Clean and normalize date string to YYYY-MM-DD"""
        if not date_str:
            return ''
        
        # If already in YYYY-MM-DD format, return as-is
        if re.match(r'\d{4}-\d{2}-\d{2}', date_str):
            return date_str
        
        # Try to parse various date formats
        date_patterns = [
            r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-M-D
            r'(\d{1,2})/(\d{1,2})/(\d{4})',  # M/D/YYYY
            r'(\d{1,2})\.(\d{1,2})\.(\d{4})', # D.M.YYYY
            r'(\d{4})(\d{2})(\d{2})',        # YYYYMMDD
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, date_str)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    try:
                        if len(groups[0]) == 4:  # First group is year
                            year, month, day = groups
                        else:  # Last group is year
                            if '/' in date_str:
                                month, day, year = groups  # US format
                            else:
                                day, month, year = groups  # European format
                        
                        # Ensure proper formatting
                        return f"{int(year):04d}-{int(month):02d}-{int(day):02d}"
                    except ValueError:
                        continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return date_str
    
