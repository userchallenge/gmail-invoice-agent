from .base_extractor import BaseExtractor
from typing import Dict, List
import logging

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
        """Extract concert data using Claude AI"""
        # Clean and prepare context for Claude
        subject = self._clean_text(email_metadata.get('subject', ''))
        body = self._clean_text(email_content)[:3000]  # Limit body length
        
        email_content_formatted = f"""
Subject: {subject}
From: {email_metadata.get('sender', '')}
Date: {email_metadata.get('date', '')}
Body: {body}
"""
        
        prompt = f"""Extract concert information from this email content for concerts in Sweden.

Email content:
{email_content_formatted}

Extract ALL concerts mentioned in Sweden regardless of venue or city.

Return JSON array of concerts:
[
    {{
        "artist": "main artist/band name",
        "venue": "venue name (exact name as mentioned)",
        "town": "city/town where venue is located",
        "date": "concert date in YYYY-MM-DD format",
        "room": "specific room if mentioned (Klubben, Stora Salen, etc.)",
        "ticket_info": "ticket sales information if mentioned"
    }}
]

Return empty array [] if no concerts in Sweden found."""
        
        # Use base class method for Claude API call
        response_text = self._call_claude(prompt, max_tokens=1500)
        if not response_text:
            return []
        
        # Parse JSON response using base class method
        concerts = self._parse_json_response(response_text, is_array=True)
        
        # Log Claude's response for debugging
        logger.info(f"Claude concert response: {response_text[:300]}...")
        
        # Add email metadata using base class method
        if concerts:
            concerts = self._add_email_metadata(concerts, email_metadata)
            logger.info(f"✓ Extracted {len(concerts)} concert(s) from: {subject[:50]}...")
        
        return concerts
    
    
