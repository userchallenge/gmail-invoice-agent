"""Tests for the ConcertExtractor class."""

import pytest
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the path so we can import extractors
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.concert_extractor import ConcertExtractor


class TestConcertExtractor:
    """Test cases for ConcertExtractor."""
    
    @pytest.fixture
    def concert_extractor(self, sample_config, mock_claude_client):
        """Create a ConcertExtractor instance for testing."""
        return ConcertExtractor(
            sample_config['extractors']['concerts'], 
            mock_claude_client
        )
    
    def test_name_property(self, concert_extractor):
        """Test that the name property returns 'concerts'."""
        assert concert_extractor.name == "concerts"
    
    def test_output_filename(self, concert_extractor):
        """Test that output filename is returned correctly."""
        assert concert_extractor.output_filename == "output/concerts.csv"
    
    def test_get_search_keywords(self, concert_extractor):
        """Test that search keywords are retrieved correctly."""
        keywords = concert_extractor.get_search_keywords()
        assert 'konsert' in keywords
        assert 'live' in keywords
        assert 'concert' in keywords
        assert 'show' in keywords
    
    def test_get_additional_search_filters(self, concert_extractor):
        """Test that no additional filters are returned for concerts."""
        filters = concert_extractor.get_additional_search_filters()
        assert len(filters) == 0
    
    def test_should_process_concert_email_sweden(self, concert_extractor):
        """Test that Swedish concert emails are correctly identified."""
        email_content = "Konsert med The Hives i Stockholm"
        sender = "info@venue.se"
        subject = "Live konsert - The Hives"
        
        result = concert_extractor.should_process(email_content, sender, subject)
        assert result is True
    
    def test_should_process_concert_email_english(self, concert_extractor):
        """Test that English concert emails in Sweden are correctly identified."""
        email_content = "Concert with Arctic Monkeys in Sweden, Stockholm venue"
        sender = "tickets@venue.com"
        subject = "Live show - Arctic Monkeys"
        
        result = concert_extractor.should_process(email_content, sender, subject)
        assert result is True
    
    def test_should_not_process_non_sweden_concert(self, concert_extractor):
        """Test that non-Sweden concerts are rejected."""
        email_content = "Concert with The Beatles in London"
        sender = "info@venue.co.uk"
        subject = "Live show - The Beatles"
        
        result = concert_extractor.should_process(email_content, sender, subject)
        assert result is False
    
    def test_should_not_process_non_concert_email(self, concert_extractor):
        """Test that non-concert emails are correctly rejected."""
        email_content = "Welcome to our newsletter from Sweden!"
        sender = "marketing@company.se"
        subject = "Weekly Updates"
        
        result = concert_extractor.should_process(email_content, sender, subject)
        assert result is False
    
    def test_extract_with_valid_concerts(self, concert_extractor, sample_email_metadata, mock_claude_client):
        """Test extraction of valid concert data."""
        # Mock Claude response with concert array
        mock_content = Mock()
        mock_content.text = '''
        [
            {
                "artist": "Arctic Monkeys",
                "venue": "Annexet",
                "town": "Stockholm",
                "date": "2025-03-15",
                "room": "Main Hall",
                "ticket_info": "Tickets on sale Friday"
            },
            {
                "artist": "The Hives",
                "venue": "Ullevi",
                "town": "Göteborg", 
                "date": "2025-04-20",
                "room": "",
                "ticket_info": "Sold out"
            }
        ]
        '''
        mock_claude_client.messages.create.return_value.content = [mock_content]
        
        email_content = "Concerts in Sweden: Arctic Monkeys and The Hives"
        results = concert_extractor.extract(email_content, sample_email_metadata)
        
        assert len(results) == 2
        
        # Check first concert
        first_concert = results[0]
        assert first_concert['artist'] == 'Arctic Monkeys'
        assert first_concert['venue'] == 'Annexet'
        assert first_concert['town'] == 'Stockholm'
        assert first_concert['date'] == '2025-03-15'
        
        # Check second concert
        second_concert = results[1]
        assert second_concert['artist'] == 'The Hives'
        assert second_concert['venue'] == 'Ullevi'
        assert second_concert['town'] == 'Göteborg'
    
    def test_extract_with_no_concerts(self, concert_extractor, sample_email_metadata, mock_claude_client):
        """Test extraction when no concerts are found."""
        # Mock Claude response with empty array
        mock_content = Mock()
        mock_content.text = '[]'
        mock_claude_client.messages.create.return_value.content = [mock_content]
        
        email_content = "This email has no concert information"
        results = concert_extractor.extract(email_content, sample_email_metadata)
        
        assert len(results) == 0
    
    def test_extract_with_single_concert_object(self, concert_extractor, sample_email_metadata, mock_claude_client):
        """Test extraction when Claude returns single object instead of array."""
        # Mock Claude response with single object
        mock_content = Mock()
        mock_content.text = '''
        {
            "artist": "Veronica Maggio",
            "venue": "Malmö Arena",
            "town": "Malmö",
            "date": "2025-05-10",
            "room": "",
            "ticket_info": "Early bird tickets"
        }
        '''
        mock_claude_client.messages.create.return_value.content = [mock_content]
        
        email_content = "Concert with Veronica Maggio in Malmö"
        results = concert_extractor.extract(email_content, sample_email_metadata)
        
        assert len(results) == 1
        result = results[0]
        assert result['artist'] == 'Veronica Maggio'
        assert result['venue'] == 'Malmö Arena'
        assert result['town'] == 'Malmö'