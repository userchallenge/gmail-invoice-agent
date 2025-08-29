"""Tests for GmailServer date range functionality."""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime
import sys
import os

# Add the parent directory to the path so we can import gmail_server
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_server import GmailServer


class TestGmailServerDateRange:
    """Test cases for GmailServer date range functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        return {
            'processing': {
                'max_emails': 100
            }
        }
    
    def test_build_search_query_with_end_date(self, mock_config):
        """Test _build_search_query with end date."""
        # Mock the Gmail service initialization
        with patch('gmail_server.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            # Create GmailServer instance with mock credentials
            with patch('gmail_server.Credentials'), \
                 patch('gmail_server.InstalledAppFlow'), \
                 patch('os.path.exists', return_value=True):
                
                gmail_server = GmailServer('fake_creds.json', 'fake_token.json', ['scope'], mock_config)
                
                # Test date range query
                start_date = datetime(2025, 6, 30)
                end_date = datetime(2025, 7, 1)
                keywords = ['invoice', 'faktura']
                
                query = gmail_server._build_search_query(start_date, keywords, None, end_date)
                
                # Should include both after and before
                assert 'after:2025/06/30' in query
                assert 'before:2025/07/01' in query
                assert 'invoice' in query
                assert 'faktura' in query
    
    def test_build_search_query_without_end_date(self, mock_config):
        """Test _build_search_query without end date (original behavior)."""
        # Mock the Gmail service initialization
        with patch('gmail_server.build') as mock_build:
            mock_service = Mock()
            mock_build.return_value = mock_service
            
            # Create GmailServer instance with mock credentials
            with patch('gmail_server.Credentials'), \
                 patch('gmail_server.InstalledAppFlow'), \
                 patch('os.path.exists', return_value=True):
                
                gmail_server = GmailServer('fake_creds.json', 'fake_token.json', ['scope'], mock_config)
                
                # Test single date query (original behavior)
                start_date = datetime(2025, 6, 30)
                keywords = ['invoice']
                
                query = gmail_server._build_search_query(start_date, keywords)
                
                # Should only include after
                assert 'after:2025/06/30' in query
                assert 'before:' not in query
                assert 'invoice' in query
    
    def test_fetch_emails_for_extractors_with_date_range(self, mock_config):
        """Test fetch_emails_for_extractors with date range configuration."""
        # Add date range configuration
        date_range_config = mock_config.copy()
        date_range_config['processing'].update({
            'use_date_range': True,
            'from_date': '2025-06-30',
            'to_date': '2025-07-01'
        })
        
        # Mock the Gmail service initialization and API calls
        with patch('gmail_server.build') as mock_build:
            mock_service = Mock()
            mock_service.users().messages().list().execute.return_value = {'messages': []}
            mock_build.return_value = mock_service
            
            # Create GmailServer instance with mock credentials
            with patch('gmail_server.Credentials'), \
                 patch('gmail_server.InstalledAppFlow'), \
                 patch('os.path.exists', return_value=True):
                
                gmail_server = GmailServer('fake_creds.json', 'fake_token.json', ['scope'], date_range_config)
                
                # Mock the _build_search_query to verify it gets called with correct parameters
                with patch.object(gmail_server, '_build_search_query', return_value='mocked_query') as mock_build_query:
                    
                    keywords = ['invoice']
                    result = gmail_server.fetch_emails_for_extractors(keywords)
                    
                    # Verify _build_search_query was called with end_date
                    mock_build_query.assert_called_once()
                    call_args = mock_build_query.call_args[0]
                    
                    # Should have start_date, keywords, additional_filters, end_date
                    assert len(call_args) == 4
                    start_date, passed_keywords, additional_filters, end_date = call_args
                    
                    # Verify dates (end_date gets +1 day to make it inclusive)
                    assert start_date.strftime('%Y-%m-%d') == '2025-06-30'
                    assert end_date.strftime('%Y-%m-%d') == '2025-07-02'  # +1 day for inclusivity
                    assert passed_keywords == keywords
    
    def test_fetch_emails_for_extractors_without_date_range(self, mock_config):
        """Test fetch_emails_for_extractors without date range (original behavior)."""
        # Mock the Gmail service initialization and API calls
        with patch('gmail_server.build') as mock_build:
            mock_service = Mock()
            mock_service.users().messages().list().execute.return_value = {'messages': []}
            mock_build.return_value = mock_service
            
            # Create GmailServer instance with mock credentials
            with patch('gmail_server.Credentials'), \
                 patch('gmail_server.InstalledAppFlow'), \
                 patch('os.path.exists', return_value=True):
                
                gmail_server = GmailServer('fake_creds.json', 'fake_token.json', ['scope'], mock_config)
                
                # Mock the _build_search_query to verify it gets called with correct parameters
                with patch.object(gmail_server, '_build_search_query', return_value='mocked_query') as mock_build_query:
                    
                    keywords = ['invoice']
                    result = gmail_server.fetch_emails_for_extractors(keywords, days_back=7)
                    
                    # Verify _build_search_query was called without end_date
                    mock_build_query.assert_called_once()
                    call_args = mock_build_query.call_args[0]
                    
                    # Should have start_date, keywords, additional_filters (no end_date)
                    assert len(call_args) == 3
                    start_date, passed_keywords, additional_filters = call_args
                    
                    assert passed_keywords == keywords