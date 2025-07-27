import anthropic
import logging
import re
from typing import Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class EmailClassifier:
    def __init__(self, api_key: str, config: Dict):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.config = config
        self.invoice_keywords = config['invoice_keywords']
        self.common_vendors = config['common_vendors']
        
    def classify_and_extract(self, email: Dict) -> Optional[Dict]:
        """Classify email and extract invoice data if it's an invoice"""
        try:
            # First do a quick keyword check
            if not self._has_invoice_indicators(email):
                logger.debug(f"No invoice indicators found in: {email['subject']}")
                return None
            
            logger.info(f"Processing potential invoice: {email['subject']}")
            
            # Use Claude to classify and extract
            invoice_data = self._extract_with_claude(email)
            
            if invoice_data and invoice_data.get('is_invoice'):
                logger.info(f"✓ Extracted invoice from {invoice_data.get('vendor', 'Unknown')}")
                return self._format_invoice_data(invoice_data, email)
            else:
                logger.debug(f"Claude determined this is not an invoice: {email['subject']}")
                return None
                
        except Exception as e:
            logger.error(f"Error processing email {email['subject']}: {e}")
            return None
    
    def _has_invoice_indicators(self, email: Dict) -> bool:
        """Quick check for invoice indicators in subject and sender"""
        text_to_check = f"{email['subject']} {email['sender']}".lower()
        
        # Check Swedish indicators (prioritized)
        swedish_indicators = self.invoice_keywords['invoice_indicators']['swedish']
        for indicator in swedish_indicators:
            if indicator.lower() in text_to_check:
                return True
        
        # Check English indicators
        english_indicators = self.invoice_keywords['invoice_indicators']['english']
        for indicator in english_indicators:
            if indicator.lower() in text_to_check:
                return True
        
        # Check for PDF attachments (common for invoices)
        for attachment in email.get('attachments', []):
            if attachment.get('filename', '').lower().endswith('.pdf'):
                return True
                
        return False
    
    def _extract_with_claude(self, email: Dict) -> Optional[Dict]:
        """Use Claude to extract invoice data"""
        try:
            # Clean and prepare context for Claude (handle encoding issues)
            subject = self._clean_text(email.get('subject', ''))
            sender = self._clean_text(email.get('sender', ''))
            body = self._clean_text(email.get('body', ''))[:2000]  # Limit body length
            
            # Include PDF content if available
            pdf_content = ""
            if email.get('pdf_processed') and email.get('pdf_text'):
                pdf_text = self._clean_text(email.get('pdf_text', ''))[:3000]  # Limit PDF text length
                pdf_filename = email.get('pdf_filename', 'unknown.pdf')
                pdf_content = f"""

--- PDF ATTACHMENT CONTENT ---
PDF File: {pdf_filename}
PDF Text:
{pdf_text}
--- END PDF CONTENT ---
"""
            
            email_content = f"""
Subject: {subject}
From: {sender}
Date: {email.get('date', '')}
Body: {body}

Attachments: {[self._clean_text(att.get('filename', '')) for att in email.get('attachments', [])]}
{pdf_content}
"""
            
            prompt = f"""You are an expert at identifying and extracting data from Swedish and English invoices in emails and PDF attachments.

Analyze this email (including any PDF attachment content) and determine:
1. Is this a legitimate invoice/bill (not promotional, not receipt, not notification)?
2. If yes, extract the following information:

Email Content:
{email_content}

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

            # Clean the entire prompt to avoid encoding issues
            cleaned_prompt = self._clean_text(prompt)
            
            # Debug: log the cleaned prompt to check for encoding issues
            logger.debug(f"Sending prompt to Claude (first 200 chars): {cleaned_prompt[:200]!r}")

            message = self.client.messages.create(
                model=self.config['claude']['model'],
                max_tokens=1000,
                messages=[{"role": "user", "content": cleaned_prompt}]
            )
            
            # Extract text from Claude's response
            try:
                response_text = message.content[0].text.strip()
            except AttributeError:
                # Fallback for different content types
                response_text = str(message.content[0]).strip()
            
            # Parse JSON response
            try:
                # Clean up response (remove any markdown formatting)
                json_text = response_text
                if "```json" in json_text:
                    json_text = json_text.split("```json")[1].split("```")[0]
                elif "```" in json_text:
                    json_text = json_text.split("```")[1].split("```")[0]
                
                # Try to extract just the JSON part if there's extra text
                original_response = json_text
                if "{" in json_text and "}" in json_text:
                    start = json_text.find("{")
                    # Find the closing brace by counting braces
                    brace_count = 0
                    end = start
                    for i, char in enumerate(json_text[start:], start):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end = i + 1
                                break
                    json_text = json_text[start:end]
                
                invoice_data = json.loads(json_text)
                
                # Log Claude's reasoning if there was extra text beyond JSON
                if len(original_response.strip()) > len(json_text.strip()):
                    reasoning = original_response[len(json_text):].strip()
                    if reasoning:
                        logger.info(f"Claude's reasoning: {reasoning}")
                
                return invoice_data
                
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse Claude response as JSON: {e}")
                logger.error(f"Response was: {response_text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling Claude API: {e}")
            return None
    
    def _format_invoice_data(self, claude_data: Dict, email: Dict) -> Dict:
        """Format the extracted data for CSV export"""
        return {
            'email_id': email['id'],
            'email_subject': email['subject'],
            'email_sender': email['sender'],
            'email_date': email['date'],
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
            'pdf_processed': email.get('pdf_processed', False),
            'pdf_filename': email.get('pdf_filename', ''),
            'pdf_text_length': email.get('pdf_text_length', 0),
            'pdf_processing_error': email.get('pdf_processing_error', '')
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
    
    def _clean_text(self, text: str) -> str:
        """Clean text to handle encoding issues and special characters"""
        if not text:
            return ""
        
        # Convert to string if not already
        text = str(text)
        
        # Replace or remove problematic characters
        # Replace common problematic characters
        replacements = {
            '\xb4': "'",  # Acute accent
            '\u2019': "'",  # Right single quotation mark
            '\u2018': "'",  # Left single quotation mark
            '\u201c': '"',  # Left double quotation mark
            '\u201d': '"',  # Right double quotation mark
            '\u2013': '-',  # En dash
            '\u2014': '-',  # Em dash
            '\u00a0': ' ',  # Non-breaking space
        }
        
        for old_char, new_char in replacements.items():
            text = text.replace(old_char, new_char)
        
        # Remove any remaining non-printable characters
        text = ''.join(char for char in text if char.isprintable() or char.isspace())
        
        # Ensure we can encode to UTF-8
        try:
            text.encode('utf-8')
            return text
        except UnicodeEncodeError:
            # If still problematic, replace non-ASCII with safe alternatives
            return text.encode('ascii', errors='replace').decode('ascii')
        except Exception:
            # Last resort: return empty string
            return ""