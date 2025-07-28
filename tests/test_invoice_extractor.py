"""Tests for the InvoiceExtractor class."""

import pytest
import sys
import os
from unittest.mock import Mock

# Add the parent directory to the path so we can import extractors
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extractors.invoice_extractor import InvoiceExtractor


class TestInvoiceExtractor:
    """Test cases for InvoiceExtractor."""
    
    @pytest.fixture
    def invoice_extractor(self, sample_config, mock_claude_client):
        """Create an InvoiceExtractor instance for testing."""
        return InvoiceExtractor(
            sample_config['extractors']['invoices'], 
            mock_claude_client
        )
    
    def test_name_property(self, invoice_extractor):
        """Test that the name property returns 'invoices'."""
        assert invoice_extractor.name == "invoices"
    
    def test_output_filename(self, invoice_extractor):
        """Test that output filename is returned correctly."""
        assert invoice_extractor.output_filename == "output/invoices.csv"
    
    def test_get_search_keywords(self, invoice_extractor):
        """Test that search keywords are retrieved correctly."""
        keywords = invoice_extractor.get_search_keywords()
        assert 'faktura' in keywords
        assert 'räkning' in keywords
        assert 'invoice' in keywords
        assert 'bill' in keywords
    
    def test_get_additional_search_filters(self, invoice_extractor):
        """Test that PDF attachment filter is returned."""
        filters = invoice_extractor.get_additional_search_filters()
        assert "has:attachment filename:pdf" in filters
    
    def test_should_process_invoice_email(self, invoice_extractor):
        """Test that invoice emails are correctly identified."""
        email_content = "Your invoice is ready for payment"
        sender = "billing@company.com"
        subject = "Invoice INV-001"
        
        result = invoice_extractor.should_process(email_content, sender, subject)
        assert result is True
    
    def test_should_not_process_non_invoice_email(self, invoice_extractor):
        """Test that non-invoice emails are correctly rejected."""
        email_content = "Welcome to our newsletter!"
        sender = "marketing@company.com"
        subject = "Weekly Updates"
        
        result = invoice_extractor.should_process(email_content, sender, subject)
        assert result is False
    
    def test_clean_amount(self, invoice_extractor):
        """Test amount cleaning functionality."""
        assert invoice_extractor._clean_amount("25.50 kr") == "25.5"
        assert invoice_extractor._clean_amount("1,250.00") == "1250.0"
        assert invoice_extractor._clean_amount("€100") == "100.0"
    
    def test_clean_date(self, invoice_extractor):
        """Test date cleaning functionality."""
        assert invoice_extractor._clean_date("2025-01-15") == "2025-01-15"
        # US format: month/day/year -> year-month-day
        assert invoice_extractor._clean_date("01/15/2025") == "2025-01-15"
        # European format: day.month.year -> year-month-day
        assert invoice_extractor._clean_date("15.01.2025") == "2025-01-15"
    
    def test_extract_with_valid_invoice(self, invoice_extractor, sample_email_metadata, mock_claude_client):
        """Test extraction of valid invoice data."""
        # Mock Claude response for valid invoice
        mock_content = Mock()
        mock_content.text = '''
        {
            "is_invoice": true,
            "vendor": "Test Company",
            "invoice_number": "INV-001",
            "amount": "100.00",
            "currency": "SEK",
            "due_date": "2025-02-15",
            "invoice_date": "2025-01-15",
            "ocr": "",
            "description": "Test service",
            "confidence": 0.95
        }
        '''
        mock_claude_client.messages.create.return_value.content = [mock_content]
        
        email_content = "Invoice from Test Company for 100 SEK"
        results = invoice_extractor.extract(email_content, sample_email_metadata)
        
        assert len(results) == 1
        result = results[0]
        assert result['vendor'] == 'Test Company'
        assert result['amount'] == '100.0'
        assert result['currency'] == 'SEK'
    
    def test_extract_with_non_invoice(self, invoice_extractor, sample_email_metadata, mock_claude_client):
        """Test extraction when email is not an invoice."""
        # Mock Claude response for non-invoice
        mock_content = Mock()
        mock_content.text = '{"is_invoice": false}'
        mock_claude_client.messages.create.return_value.content = [mock_content]
        
        email_content = "This is just a regular email"
        results = invoice_extractor.extract(email_content, sample_email_metadata)
        
        assert len(results) == 0
    
    def test_template_formatting(self, invoice_extractor, sample_email_metadata):
        """Test that the prompt template is properly formatted with variables."""
        email_content = "Test invoice content"
        
        # Test the template formatting method
        formatted_prompt = invoice_extractor._format_prompt_template(email_content, sample_email_metadata)
        
        # Check that template variables were replaced
        assert '{email_content}' not in formatted_prompt
        assert '{swedish_keywords}' not in formatted_prompt  
        assert '{english_keywords}' not in formatted_prompt
        
        # Check that keywords were properly inserted
        assert 'faktura, räkning' in formatted_prompt
        assert 'invoice, bill' in formatted_prompt
        
        # Check that email content was included
        assert 'Test invoice content' in formatted_prompt
        assert sample_email_metadata['subject'] in formatted_prompt