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
        """Extract invoice data using Claude AI with configurable prompt template"""
        try:
            # Use the base class template formatting method
            prompt = self._format_prompt_template(email_content, email_metadata)
            
            # Use base class method for Claude API call
            response_text = self._call_claude(prompt, max_tokens=1000)
            if not response_text:
                return []
            
            # Parse Claude response using base class method
            extracted_data = self._parse_json_response(response_text, is_array=False)
            
            # Ensure extracted_data is a dict (type safety)
            if not isinstance(extracted_data, dict):
                extracted_data = {}
            
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
    
