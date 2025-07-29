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
        """Extract invoice data using Claude AI with configurable prompt template and reasoning capture"""
        try:
            # Save email backup for reference
            backup_path = self._save_email_backup(email_content, email_metadata)
            
            # Use the base class template formatting method
            prompt = self._format_prompt_template(email_content, email_metadata)
            
            # Use base class method for Claude API call
            response_text = self._call_claude(prompt, max_tokens=1000)
            if not response_text:
                # Create record for failed Claude call
                return [self._create_failed_processing_record(email_content, email_metadata, backup_path, "No response from Claude")]
            
            # Parse Claude response and extract reasoning
            extracted_data, reasoning_data = self._parse_json_response(response_text, is_array=False)
            
            # Ensure extracted_data is a dict (type safety)
            if not isinstance(extracted_data, dict):
                extracted_data = {}
            
            # Create comprehensive record for ALL emails (accepted and rejected)
            if extracted_data and extracted_data.get('is_invoice'):
                # Format accepted invoice data
                formatted_data = self._format_accepted_invoice_data(extracted_data, email_metadata, reasoning_data, backup_path, email_content)
                logger.info(f"✓ Extracted invoice from {extracted_data.get('vendor', 'Unknown')}")
                return [formatted_data]
            else:
                # Format rejected email data
                formatted_data = self._format_rejected_invoice_data(extracted_data, email_metadata, reasoning_data, backup_path, email_content)
                logger.debug(f"Claude determined this is not an invoice: {email_metadata.get('subject', '')}")
                return [formatted_data]
                
        except Exception as e:
            logger.error(f"Error extracting invoice data: {e}")
            return [self._create_failed_processing_record(email_content, email_metadata, "", f"Processing error: {str(e)}")]
    
    
    def _format_accepted_invoice_data(self, claude_data: Dict, email_metadata: Dict, reasoning_data: Dict, backup_path: str, email_content: str) -> Dict:
        """Format accepted invoice data for CSV export with reasoning and evaluation columns"""
        return {
            # Basic email metadata
            'email_id': email_metadata.get('id', ''),
            'email_subject': email_metadata.get('subject', ''),
            'email_sender': email_metadata.get('sender', ''),
            'email_date': email_metadata.get('date', ''),
            'email_backup_path': backup_path,
            
            # Extraction results
            'extracted': True,
            'vendor': (claude_data.get('vendor') or '').strip(),
            'invoice_number': (claude_data.get('invoice_number') or '').strip(),
            'amount': self._clean_amount(claude_data.get('amount', '')),
            'currency': (claude_data.get('currency') or 'SEK').upper(),
            'due_date': self._clean_date(claude_data.get('due_date', '')),
            'invoice_date': self._clean_date(claude_data.get('invoice_date', '')),
            'ocr': (claude_data.get('ocr') or '').strip(),
            'description': (claude_data.get('description') or '').strip(),
            'confidence': claude_data.get('confidence', 0.0),
            
            # Reasoning from Claude
            'claude_reasoning_before': reasoning_data.get('before', ''),
            'claude_reasoning_after': reasoning_data.get('after', ''),
            
            # Human evaluation (empty initially)
            'human_evaluation': '',
            'human_feedback': '',
            
            # Processing metadata
            'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _format_rejected_invoice_data(self, claude_data: Dict, email_metadata: Dict, reasoning_data: Dict, backup_path: str, email_content: str) -> Dict:
        """Format rejected email data for CSV export with reasoning"""
        return {
            # Basic email metadata
            'email_id': email_metadata.get('id', ''),
            'email_subject': email_metadata.get('subject', ''),
            'email_sender': email_metadata.get('sender', ''),
            'email_date': email_metadata.get('date', ''),
            'email_backup_path': backup_path,
            
            # Extraction results (empty for rejected)
            'extracted': False,
            'vendor': '',
            'invoice_number': '',
            'amount': '',
            'currency': '',
            'due_date': '',
            'invoice_date': '',
            'ocr': '',
            'description': '',
            'confidence': claude_data.get('confidence', 0.0) if claude_data else 0.0,
            
            # Reasoning from Claude
            'claude_reasoning_before': reasoning_data.get('before', ''),
            'claude_reasoning_after': reasoning_data.get('after', ''),
            
            # Human evaluation (empty initially)
            'human_evaluation': '',
            'human_feedback': '',
            
            # Processing metadata
            'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _create_failed_processing_record(self, email_content: str, email_metadata: Dict, backup_path: str, error_message: str) -> Dict:
        """Create record for emails that failed to process"""
        return {
            # Basic email metadata
            'email_id': email_metadata.get('id', ''),
            'email_subject': email_metadata.get('subject', ''),
            'email_sender': email_metadata.get('sender', ''),
            'email_date': email_metadata.get('date', ''),
            'email_backup_path': backup_path,
            
            # Extraction results (empty for failed)
            'extracted': False,
            'vendor': '',
            'invoice_number': '',
            'amount': '',
            'currency': '',
            'due_date': '',
            'invoice_date': '',
            'ocr': '',
            'description': '',
            'confidence': 0.0,
            
            # Reasoning from Claude (error message)
            'claude_reasoning_before': f"Processing failed: {error_message}",
            'claude_reasoning_after': '',
            
            # Human evaluation (empty initially)
            'human_evaluation': '',
            'human_feedback': '',
            
            # Processing metadata
            'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
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
    
