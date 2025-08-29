"""
Zero Inbox Email Fetcher
Extends existing Gmail functionality to support Zero Inbox workflow
Integrates with database storage and enhanced cleaning pipeline
"""

import logging
import re
from datetime import datetime
from typing import List, Dict, Tuple
from html import unescape
import html2text

from gmail_server import GmailServer
from models.zero_inbox_models import DatabaseManager, Email

logger = logging.getLogger(__name__)


class ZeroInboxEmailFetcher:
    """
    Enhanced email fetcher for Zero Inbox system
    Extends existing Gmail functionality with database integration
    """
    
    def __init__(self, config: Dict, database_manager: DatabaseManager):
        self.config = config
        self.db_manager = database_manager
        
        # Initialize Gmail server with existing configuration
        self.gmail_server = GmailServer(
            config['gmail']['credentials_file'],
            config['gmail']['token_file'],
            config['gmail']['scopes'],
            config
        )
        
        # HTML to text converter for cleaning
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
        self.html_converter.body_width = 0  # No line wrapping
        
        logger.info("✅ Zero Inbox Email Fetcher initialized")
    
    def fetch_and_store_emails(self, 
                             days_back: int = 1, 
                             max_emails: int = 100,
                             from_date: str | None = None,
                             to_date: str | None = None) -> Tuple[int, int]:
        """
        Fetch emails and store in Zero Inbox database
        
        Returns:
            Tuple of (emails_fetched, emails_stored)
        """
        logger.info("🔄 Starting Zero Inbox email fetch and store process")
        
        # Configure date range if provided
        if from_date and to_date:
            self.config['processing'] = self.config.get('processing', {})
            self.config['processing']['use_date_range'] = True
            self.config['processing']['from_date'] = from_date
            self.config['processing']['to_date'] = to_date
            logger.info(f"📅 Using date range: {from_date} to {to_date}")
        else:
            logger.info(f"📅 Using days back: {days_back}")
        
        # Fetch emails using existing Gmail functionality
        # Use broad search criteria for Zero Inbox (we want all emails)
        raw_emails = self._fetch_raw_emails(days_back, max_emails)
        
        if not raw_emails:
            logger.info("📭 No emails found")
            return 0, 0
        
        logger.info(f"📧 Fetched {len(raw_emails)} emails from Gmail")
        
        # Process and store emails
        stored_count = 0
        for i, email_data in enumerate(raw_emails):
            try:
                # Clean and process email
                cleaned_email = self._clean_and_process_email(email_data)
                
                # Store in database (with duplicate prevention)
                if self._store_email_in_database(cleaned_email):
                    stored_count += 1
                
                # Log progress
                if (i + 1) % 10 == 0:
                    logger.info(f"📊 Processed {i + 1}/{len(raw_emails)} emails...")
                    
            except Exception as e:
                logger.error(f"❌ Error processing email {email_data.get('id', 'unknown')}: {e}")
                continue
        
        logger.info(f"✅ Email fetch complete: {len(raw_emails)} fetched, {stored_count} stored")
        return len(raw_emails), stored_count
    
    def _fetch_raw_emails(self, days_back: int, max_emails: int) -> List[Dict]:
        """
        Fetch raw emails using existing Gmail server functionality
        Modified to use broader search criteria for Zero Inbox
        """
        try:
            # For Zero Inbox, we want ALL emails, not just invoices/concerts
            # Temporarily modify config to use broader search
            original_config = self.config.copy()
            
            # Use minimal search criteria - we want everything
            self.gmail_server.config = self.config
            
            # Use the existing fetch method but with broader criteria
            emails = self.gmail_server.fetch_emails(days_back, max_emails)
            
            # Restore original config
            self.config = original_config
            
            return emails
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch emails: {e}")
            return []
    
    def _clean_and_process_email(self, email_data: Dict) -> Dict:
        """
        Clean and process email data for Zero Inbox storage
        Enhanced cleaning pipeline with PDF processing
        """
        try:
            # Extract basic email information
            email_id = email_data.get('id', '')
            sender = self._clean_text(email_data.get('sender', ''))
            subject = self._clean_text(email_data.get('subject', ''))
            date_received = self._parse_date(email_data.get('date', ''))
            
            # Clean email body
            raw_body = email_data.get('body', '')
            cleaned_body = self._clean_email_body(raw_body)
            
            # Process PDF content if available
            pdf_content = None
            if email_data.get('pdf_processed', False) and email_data.get('pdf_text'):
                pdf_text = email_data.get('pdf_text')
                pdf_content = self._clean_text(pdf_text) if pdf_text else None
            
            # Store original HTML content (truncated for storage)
            html_content = raw_body[:5000] if len(raw_body) > 5000 else raw_body
            
            # Attachment information
            attachments = email_data.get('attachments', [])
            has_attachments = len(attachments) > 0
            attachment_count = len(attachments)
            
            cleaned_email = {
                'email_id': email_id,
                'sender': sender,
                'subject': subject,
                'body': cleaned_body,
                'pdf_content': pdf_content,
                'html_content': html_content,
                'date_received': date_received,
                'date_processed': datetime.now(),
                'has_attachments': has_attachments,
                'attachment_count': attachment_count
            }
            
            logger.debug(f"✅ Cleaned email: {subject[:50]}...")
            return cleaned_email
            
        except Exception as e:
            logger.error(f"❌ Error cleaning email: {e}")
            raise
    
    def _clean_email_body(self, raw_body: str) -> str:
        """
        Advanced email body cleaning pipeline
        Removes HTML while preserving structure and readability
        """
        if not raw_body:
            return ""
        
        try:
            # Decode HTML entities
            text = unescape(raw_body)
            
            # Convert HTML to text if it contains HTML tags
            if '<' in text and '>' in text:
                # Use html2text for better formatting preservation
                text = self.html_converter.handle(text)
            
            # Clean up whitespace and formatting
            text = self._clean_whitespace(text)
            
            # Remove email signatures and footers (common patterns)
            text = self._remove_signatures(text)
            
            # Limit length for database storage (keep most relevant content)
            if len(text) > 10000:
                # Keep first 8000 characters and add truncation notice
                text = text[:8000] + "\n\n[Content truncated for storage]"
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"⚠️ Email body cleaning failed, using raw text: {e}")
            return self._clean_text(raw_body)[:5000]
    
    def _clean_whitespace(self, text: str) -> str:
        """Clean up excessive whitespace while preserving structure"""
        # Remove excessive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove trailing spaces
        lines = [line.rstrip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove excessive spaces (more than 2)
        text = re.sub(r' {3,}', '  ', text)
        
        return text
    
    def _remove_signatures(self, text: str) -> str:
        """Remove common email signatures and footers"""
        # Common signature patterns
        signature_patterns = [
            r'\n--\s*\n.*',  # Standard -- signature delimiter
            r'\nSent from my iPhone.*',
            r'\nSent from my iPad.*',
            r'\nGet Outlook for iOS.*',
            r'\nGet Outlook for Android.*',
            r'\n\[cid:.*?\].*',  # Embedded images
            r'\nThis email was sent by.*',
            r'\nUnsubscribe.*?link.*',
        ]
        
        for pattern in signature_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        
        return text
    
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning for database storage"""
        if not text:
            return ""
        
        # Remove null bytes and control characters
        text = text.replace('\x00', '')
        text = re.sub(r'[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)
        
        # Normalize whitespace
        text = ' '.join(text.split())
        
        return text.strip()
    
    def _parse_date(self, date_string: str) -> datetime:
        """Parse email date string to datetime object"""
        if not date_string:
            return datetime.now()
        
        try:
            # Try parsing the existing format from gmail_server
            if isinstance(date_string, str):
                return datetime.strptime(date_string, "%Y-%m-%d %H:%M:%S")
            else:
                return datetime.now()
        except:
            logger.warning(f"⚠️ Could not parse date: {date_string}")
            return datetime.now()
    
    def _store_email_in_database(self, cleaned_email: Dict) -> bool:
        """
        Store cleaned email in database with duplicate prevention
        Returns True if email was stored, False if duplicate
        """
        try:
            session = self.db_manager.get_session()
            
            # Check for duplicates using email_id
            existing_email = session.query(Email).filter(
                Email.email_id == cleaned_email['email_id']
            ).first()
            
            if existing_email:
                logger.debug(f"⏭️  Skipping duplicate email: {cleaned_email['email_id']}")
                session.close()
                return False
            
            # Create new email record
            email_record = Email(**cleaned_email)
            session.add(email_record)
            session.commit()
            
            logger.debug(f"💾 Stored email: {email_record.subject[:50]}...")
            session.close()
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to store email {cleaned_email.get('email_id', 'unknown')}: {e}")
            if session:
                session.rollback()
                session.close()
            return False
    
    def get_stored_email_count(self) -> int:
        """Get count of stored emails in database"""
        try:
            session = self.db_manager.get_session()
            count = session.query(Email).count()
            session.close()
            return count
        except Exception as e:
            logger.error(f"❌ Failed to get email count: {e}")
            return 0
    
    def get_emails_by_date_range(self, from_date: datetime, to_date: datetime) -> List[Email]:
        """Get emails from database within date range"""
        try:
            session = self.db_manager.get_session()
            emails = session.query(Email).filter(
                Email.date_received >= from_date,
                Email.date_received <= to_date
            ).order_by(Email.date_received.desc()).all()
            
            # Detach from session
            result = []
            for email in emails:
                session.expunge(email)
                result.append(email)
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"❌ Failed to get emails by date range: {e}")
            return []