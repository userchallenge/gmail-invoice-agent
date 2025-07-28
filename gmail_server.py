import os
import base64
import email
import logging
import io
import signal
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import time
import pypdf

logger = logging.getLogger(__name__)


class GmailServer:
    def __init__(
        self,
        credentials_file: str,
        token_file: str,
        scopes: List[str],
        config: Dict = None,
    ):
        self.credentials_file = credentials_file
        self.token_file = token_file
        self.scopes = scopes
        self.config = config or {}
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
                    logger.warning(
                        f"Token refresh failed: {e}. Getting new credentials."
                    )
                    creds = None

            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found: {self.credentials_file}"
                    )

                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        self.service = build("gmail", "v1", credentials=creds)
        logger.info("Gmail authentication successful")

    def _build_search_query(
        self, start_date: datetime, keywords: List[str] = None, additional_filters: List[str] = None
    ) -> str:
        """Build Gmail search query from provided keywords and filters"""
        date_filter = f'after:{start_date.strftime("%Y/%m/%d")}'

        # Build keyword search terms
        keyword_terms = []

        if keywords:
            # Use provided keywords (from extractors)
            for keyword in keywords:
                keyword_terms.append(f"(subject:{keyword} OR {keyword})")
        else:
            # Fallback to legacy config for backward compatibility
            keyword_filters = []

            # Add invoice indicator keywords (Swedish and English)
            if self.config.get("invoice_keywords", {}).get("invoice_indicators"):
                swedish_indicators = self.config["invoice_keywords"][
                    "invoice_indicators"
                ].get("swedish", [])
                english_indicators = self.config["invoice_keywords"][
                    "invoice_indicators"
                ].get("english", [])

                for keyword in swedish_indicators + english_indicators:
                    # Search both subject and body for each keyword
                    keyword_filters.append(f"(subject:{keyword} OR {keyword})")

            # Add common vendor keywords
            if self.config.get("common_vendors"):
                swedish_vendors = self.config["common_vendors"].get("swedish", [])
                english_vendors = self.config["common_vendors"].get("english", [])

                for vendor in swedish_vendors + english_vendors:
                    # Search for vendor in sender field and body content
                    keyword_filters.append(f"(from:{vendor} OR {vendor})")

            keyword_terms = keyword_filters

        # Combine with date filter
        query_parts = [date_filter]

        # Add keyword terms
        search_terms = []
        if keyword_terms:
            search_terms.extend(keyword_terms)
        
        # Add extractor-specific filters (e.g., PDF attachments for invoices)
        if additional_filters:
            search_terms.extend(additional_filters)
        
        if search_terms:
            query_parts.append(f'({" OR ".join(search_terms)})')
        else:
            # Fallback to basic query if no keywords
            query_parts.append("(invoice OR faktura OR räkning OR bill)")

        return " ".join(query_parts)

    def fetch_emails(self, days_back: int = 30, max_emails: int = 100) -> List[Dict]:
        """Fetch emails from the last N days"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Build Gmail search query dynamically from config
            query = self._build_search_query(start_date)
            logger.info(
                f"Fetching emails with query: {query} (max {max_emails} emails)"
            )
            logger.info(
                f"Searching emails from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )

            # Get message list
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_emails)
                .execute()
            )

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} potential invoice emails")

            emails = []
            for i, message in enumerate(messages):
                try:
                    email_data = self._get_email_details(message["id"])
                    if email_data:
                        emails.append(email_data)
                        logger.info(
                            f"Processed email {i+1}/{len(messages)}: {email_data['subject'][:50]}..."
                        )

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
            message = (
                self.service.users()
                .messages()
                .get(userId="me", id=message_id, format="full")
                .execute()
            )

            headers = message["payload"].get("headers", [])

            # Extract header information
            subject = self._get_header_value(headers, "Subject") or "No Subject"
            sender = self._get_header_value(headers, "From") or "Unknown Sender"
            date_header = self._get_header_value(headers, "Date")

            # Parse date
            email_date = self._parse_email_date(date_header)

            # Get email body
            body = self._extract_email_body(message["payload"])

            # Get attachments info
            attachments = self._get_attachment_info(message["payload"])

            email_data = {
                "id": message_id,
                "subject": subject,
                "sender": sender,
                "date": email_date,
                "body": body,
                "attachments": attachments,
                "raw_headers": headers,
            }

            # Process PDF attachments if enabled
            pdf_data = self._process_pdf_attachments(message, email_data)
            email_data.update(pdf_data)

            return email_data

        except Exception as e:
            logger.error(f"Error getting email details for {message_id}: {e}")
            return None

    def _get_header_value(self, headers: List[Dict], name: str) -> Optional[str]:
        """Extract header value by name"""
        for header in headers:
            if header["name"].lower() == name.lower():
                return header["value"]
        return None

    def _parse_email_date(self, date_string: str) -> Optional[str]:
        """Parse email date string to ISO format"""
        if not date_string:
            return None

        try:
            from email.utils import parsedate_to_datetime

            dt = parsedate_to_datetime(date_string)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception as e:
            logger.warning(f"Could not parse date '{date_string}': {e}")
            return date_string

    def _extract_email_body(self, payload: Dict) -> str:
        """Extract email body text from payload"""
        body = ""

        if "parts" in payload:
            # Multipart message
            for part in payload["parts"]:
                if part["mimeType"] == "text/plain":
                    if "data" in part["body"]:
                        body += self._decode_base64(part["body"]["data"])
                elif part["mimeType"] == "text/html" and not body:
                    # Use HTML if no plain text found
                    if "data" in part["body"]:
                        body += self._decode_base64(part["body"]["data"])
        else:
            # Single part message
            if payload["mimeType"] in ["text/plain", "text/html"]:
                if "data" in payload["body"]:
                    body += self._decode_base64(payload["body"]["data"])

        return body.strip()

    def _decode_base64(self, data: str) -> str:
        """Decode base64 email content"""
        try:
            decoded_bytes = base64.urlsafe_b64decode(data)
            return decoded_bytes.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"Error decoding base64 data: {e}")
            return ""

    def _get_attachment_info(self, payload: Dict) -> List[Dict]:
        """Get information about email attachments"""
        attachments = []

        if "parts" in payload:
            for part in payload["parts"]:
                filename = part.get("filename", "")
                if filename and part["body"].get("attachmentId"):
                    attachments.append(
                        {
                            "filename": filename,
                            "mimeType": part["mimeType"],
                            "size": part["body"].get("size", 0),
                            "attachmentId": part["body"]["attachmentId"],
                        }
                    )

        return attachments

    def _download_pdf_attachment(
        self, attachment_id: str, message_id: str, filename: str, size: int
    ) -> Optional[bytes]:
        """Download PDF attachment from Gmail and return bytes"""
        try:
            # Check size limit
            max_size_mb = (
                self.config.get("processing", {})
                .get("pdf_processing", {})
                .get("max_pdf_size_mb", 10)
            )
            size_mb = size / (1024 * 1024)

            if size_mb > max_size_mb:
                logger.warning(
                    f"PDF {filename} too large ({size_mb:.1f}MB > {max_size_mb}MB), skipping"
                )
                return None

            logger.info(f"Downloading PDF attachment: {filename} ({size_mb:.1f}MB)")

            attachment = (
                self.service.users()
                .messages()
                .attachments()
                .get(userId="me", messageId=message_id, id=attachment_id)
                .execute()
            )

            # Decode the attachment data
            file_data = base64.urlsafe_b64decode(attachment["data"])
            logger.info(f"✓ PDF downloaded: {filename}")
            return file_data

        except Exception as e:
            logger.error(f"Error downloading PDF {filename}: {e}")
            return None

    def _extract_pdf_text(self, pdf_bytes: bytes, filename: str) -> Optional[str]:
        """Extract text from PDF bytes with timeout and error handling"""
        if (
            not self.config.get("processing", {})
            .get("pdf_processing", {})
            .get("enabled", True)
        ):
            return None

        timeout_seconds = (
            self.config.get("processing", {})
            .get("pdf_processing", {})
            .get("timeout_seconds", 30)
        )

        def timeout_handler(signum, frame):
            raise TimeoutError("PDF extraction timed out")

        try:
            logger.info(f"Extracting text from PDF: {filename}")

            # Set timeout
            signal.signal(signal.SIGALRM, timeout_handler)
            signal.alarm(timeout_seconds)

            try:
                # Create PDF reader from bytes
                pdf_stream = io.BytesIO(pdf_bytes)
                pdf_reader = pypdf.PdfReader(pdf_stream)

                # Check if password protected
                if pdf_reader.is_encrypted:
                    skip_protected = (
                        self.config.get("processing", {})
                        .get("pdf_processing", {})
                        .get("skip_password_protected", True)
                    )
                    if skip_protected:
                        logger.warning(
                            f"PDF {filename} is password protected, skipping"
                        )
                        return None
                    else:
                        # Try empty password
                        if not pdf_reader.decrypt(""):
                            logger.warning(f"Could not decrypt PDF {filename}")
                            return None

                # Extract text from all pages
                text_content = []
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(page_text)
                    except Exception as e:
                        logger.warning(
                            f"Error extracting text from page {page_num + 1} of {filename}: {e}"
                        )
                        continue

                # Combine all text
                full_text = "\n".join(text_content)

                if full_text.strip():
                    logger.info(
                        f"✓ PDF text extracted: {len(full_text)} characters from {filename}"
                    )
                    return full_text
                else:
                    logger.warning(f"No text found in PDF {filename}")
                    return None

            finally:
                # Clear timeout
                signal.alarm(0)

        except TimeoutError:
            logger.error(f"PDF text extraction timed out for {filename}")
            return None
        except Exception as e:
            logger.error(f"Error extracting text from PDF {filename}: {e}")
            return None

    def _process_pdf_attachments(self, message: Dict, email_data: Dict) -> Dict:
        """Process PDF attachments and add text to email data"""
        pdf_data = {
            "pdf_processed": False,
            "pdf_filename": "",
            "pdf_text_length": 0,
            "pdf_processing_error": "",
            "pdf_text": "",
        }

        # Skip if PDF processing disabled
        if (
            not self.config.get("processing", {})
            .get("pdf_processing", {})
            .get("enabled", True)
        ):
            return pdf_data

        # Find PDF attachments
        pdf_attachments = [
            att
            for att in email_data.get("attachments", [])
            if att.get("filename", "").lower().endswith(".pdf")
        ]

        if not pdf_attachments:
            return pdf_data

        # Process first PDF attachment (can be extended for multiple PDFs)
        pdf_attachment = pdf_attachments[0]
        filename = pdf_attachment["filename"]

        try:
            # Download PDF
            pdf_bytes = self._download_pdf_attachment(
                pdf_attachment["attachmentId"],
                email_data["id"],
                filename,
                pdf_attachment.get("size", 0),
            )

            if pdf_bytes:
                # Extract text
                pdf_text = self._extract_pdf_text(pdf_bytes, filename)

                if pdf_text:
                    pdf_data.update(
                        {
                            "pdf_processed": True,
                            "pdf_filename": filename,
                            "pdf_text_length": len(pdf_text),
                            "pdf_text": pdf_text,
                        }
                    )
                else:
                    pdf_data.update(
                        {
                            "pdf_filename": filename,
                            "pdf_processing_error": "No text extracted from PDF",
                        }
                    )
            else:
                pdf_data.update(
                    {
                        "pdf_filename": filename,
                        "pdf_processing_error": "Failed to download PDF",
                    }
                )

        except Exception as e:
            logger.error(f"Error processing PDF {filename}: {e}")
            pdf_data.update({"pdf_filename": filename, "pdf_processing_error": str(e)})

        return pdf_data

    def fetch_emails_for_extractors(
        self, keywords: List[str], additional_filters: List[str] = None, days_back: int = 30
    ) -> List[Dict]:
        """Fetch emails using combined keywords and filters from all extractors"""
        try:
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)

            # Build Gmail search query using provided keywords and filters
            query = self._build_search_query(start_date, keywords, additional_filters)
            logger.info(f"Fetching emails with extractor query: {query}")
            logger.info(
                f"Searching emails from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            )

            # Get message list
            max_emails = self.config.get("processing", {}).get("max_emails", 100)
            results = (
                self.service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_emails)
                .execute()
            )

            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} emails matching extractor criteria")

            emails = []
            for i, message in enumerate(messages):
                try:
                    email_data = self._get_email_details(message["id"])
                    if email_data:
                        emails.append(email_data)
                        logger.debug(
                            f"Processed email {i+1}/{len(messages)}: {email_data['subject'][:50]}..."
                        )

                    # Rate limiting - be nice to Gmail API
                    if i > 0 and i % 10 == 0:
                        time.sleep(1)

                except Exception as e:
                    logger.error(f"Error processing message {message['id']}: {e}")
                    continue

            logger.info(f"Successfully processed {len(emails)} emails for extractors")
            return emails

        except HttpError as error:
            logger.error(f"Gmail API error: {error}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching emails: {e}")
            return []

    def get_email_content(self, email_id: str) -> str:
        """Get combined email content (body + PDF text) for processing"""
        try:
            email_data = self._get_email_details(email_id)
            if not email_data:
                return ""

            # Start with email body
            content = email_data.get("body", "")

            # Add PDF content if available
            if email_data.get("pdf_processed") and email_data.get("pdf_text"):
                pdf_text = email_data.get("pdf_text", "")
                content += f"\n\n--- PDF CONTENT ---\n{pdf_text}\n--- END PDF ---"

            return content

        except Exception as e:
            logger.error(f"Error getting email content for {email_id}: {e}")
            return ""
