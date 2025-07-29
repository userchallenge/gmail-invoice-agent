from .base_extractor import BaseExtractor
from typing import Dict, List
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class ConcertExtractor(BaseExtractor):
    """Extracts concert information from emails"""
    
    @property
    def name(self) -> str:
        return "concerts"
        
    @property
    def output_filename(self) -> str:
        return self.config.get('output_file', 'output/concerts.csv')
    
    def should_process(self, email_content: str, sender: str, subject: str) -> bool:
        """Check if email contains concert information"""
        # Check for concert keywords
        concert_keywords = self.get_search_keywords()
        content_to_check = f"{subject} {email_content}".lower()
        has_concert_keywords = self._check_keywords_in_content(content_to_check, concert_keywords)
        
        # Check for Swedish indicators (Sweden, svenska, svensk, etc.)
        swedish_indicators = ["sweden", "sverige", "svenska", "svensk", "stockholm", "göteborg", "malmö", "uppsala", "västerås", "örebro", "linköping", "helsingborg", "jönköping", "norrköping"]
        has_swedish_location = self._check_keywords_in_content(content_to_check, swedish_indicators)
        
        return has_concert_keywords and has_swedish_location
    
    def get_additional_search_filters(self) -> List[str]:
        """Concert extractors don't need additional filters like PDF attachments"""
        return []
    
    def extract(self, email_content: str, email_metadata: Dict) -> List[Dict]:
        """Extract concert data using Claude AI with configurable prompt template and reasoning capture"""
        try:
            # Save email backup for reference
            backup_path = self._save_email_backup(email_content, email_metadata)
            
            # Use the base class template formatting method
            prompt = self._format_prompt_template(email_content, email_metadata)
            
            # Use base class method for Claude API call
            response_text = self._call_claude(prompt, max_tokens=1500)
            if not response_text:
                # Create record for failed Claude call
                return [self._create_failed_processing_record(email_content, email_metadata, backup_path, "No response from Claude")]
            
            # Parse JSON response and extract reasoning
            concerts, reasoning_data = self._parse_json_response(response_text, is_array=True)
            
            # Ensure concerts is always a list (type safety)
            if not isinstance(concerts, list):
                concerts = []
            
            # Log Claude's response for debugging
            logger.debug(f"Claude concert response: {response_text[:300]}...")
            
            # Create comprehensive records for ALL processed emails
            if concerts:
                # Format accepted concert data with reasoning
                formatted_concerts = []
                for concert in concerts:
                    # Ensure confidence score exists
                    if 'confidence' not in concert:
                        concert['confidence'] = 0.8  # Default confidence for concerts
                    
                    formatted_concert = self._format_accepted_concert_data(concert, email_metadata, reasoning_data, backup_path, email_content)
                    formatted_concerts.append(formatted_concert)
                
                subject = self._clean_text(email_metadata.get('subject', ''))
                logger.info(f"✓ Extracted {len(concerts)} concert(s) from: {subject[:50]}...")
                return formatted_concerts
            else:
                # Create record for email with no concerts found
                formatted_data = self._format_rejected_concert_data(email_metadata, reasoning_data, backup_path, email_content)
                subject = self._clean_text(email_metadata.get('subject', ''))
                logger.debug(f"No concerts found in: {subject[:50]}...")
                return [formatted_data]
            
        except Exception as e:
            logger.error(f"Error extracting concert data: {e}")
            return [self._create_failed_processing_record(email_content, email_metadata, "", f"Processing error: {str(e)}")]
    
    def _format_accepted_concert_data(self, concert_data: Dict, email_metadata: Dict, reasoning_data: Dict, backup_path: str, email_content: str) -> Dict:
        """Format accepted concert data for CSV export with reasoning and evaluation columns"""
        return {
            # Basic email metadata
            'email_id': email_metadata.get('id', ''),
            'email_subject': email_metadata.get('subject', ''),
            'email_sender': email_metadata.get('sender', ''),
            'email_date': email_metadata.get('date', ''),
            'email_backup_path': backup_path,
            
            # Extraction results
            'extracted': True,
            'artist': concert_data.get('artist', ''),
            'venue': concert_data.get('venue', ''),
            'town': concert_data.get('town', ''),
            'date': concert_data.get('date', ''),
            'room': concert_data.get('room', ''),
            'ticket_info': concert_data.get('ticket_info', ''),
            'confidence': concert_data.get('confidence', 0.8),
            
            # Reasoning from Claude
            'claude_reasoning_before': reasoning_data.get('before', ''),
            'claude_reasoning_after': reasoning_data.get('after', ''),
            
            # Human evaluation (empty initially)
            'human_evaluation': '',
            'human_feedback': '',
            
            # Processing metadata
            'processing_timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _format_rejected_concert_data(self, email_metadata: Dict, reasoning_data: Dict, backup_path: str, email_content: str) -> Dict:
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
            'artist': '',
            'venue': '',
            'town': '',
            'date': '',
            'room': '',
            'ticket_info': '',
            'confidence': 0.0,
            
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
            'artist': '',
            'venue': '',
            'town': '',
            'date': '',
            'room': '',
            'ticket_info': '',
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
    
    
