"""Simplified tests for PDF processing functionality."""

import pytest
import sys
import os
from unittest.mock import Mock, patch

# Add the parent directory to the path so we can import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gmail_server import GmailServer


class TestPDFSimple:
    """Simplified test cases for PDF processing functionality."""
    
    @pytest.fixture
    def gmail_server(self, sample_config):
        """Create a GmailServer instance for testing."""
        with patch('gmail_server.build'), \
             patch('gmail_server.Credentials'), \
             patch('gmail_server.InstalledAppFlow'), \
             patch.object(GmailServer, '_authenticate'):
            server = GmailServer(
                'test_credentials.json',
                'test_token.json', 
                ['test_scope'],
                sample_config
            )
            server.service = Mock()
            return server
    
    def test_extract_pdf_text_success(self, gmail_server):
        """Test successful PDF text extraction with pypdf."""
        pdf_bytes = b"mock_pdf_content"
        filename = "test_invoice.pdf"
        
        # Mock pypdf.PdfReader to return our test content
        with patch('gmail_server.pypdf.PdfReader') as mock_reader:
            mock_pdf_instance = Mock()
            mock_pdf_instance.is_encrypted = False
            mock_page = Mock()
            mock_page.extract_text.return_value = "Invoice text from PDF"
            mock_pdf_instance.pages = [mock_page]
            mock_reader.return_value = mock_pdf_instance
            
            with patch('gmail_server.signal.signal'), \
                 patch('gmail_server.signal.alarm'):
                
                result = gmail_server._extract_pdf_text(pdf_bytes, filename)
        
        assert result == "Invoice text from PDF"
        mock_reader.assert_called_once()
    
    def test_extract_pdf_text_pypdf_import_works(self, gmail_server):
        """Test that pypdf is properly imported and can be used."""
        pdf_bytes = b"mock_pdf_content"
        filename = "test_invoice.pdf"
        
        # This test verifies that our pypdf import replacement works
        with patch('gmail_server.pypdf.PdfReader') as mock_reader:
            mock_pdf_instance = Mock()
            mock_pdf_instance.is_encrypted = False
            mock_page = Mock()
            mock_page.extract_text.return_value = "PDF content"
            mock_pdf_instance.pages = [mock_page]
            mock_reader.return_value = mock_pdf_instance
            
            with patch('gmail_server.signal.signal'), \
                 patch('gmail_server.signal.alarm'):
                
                result = gmail_server._extract_pdf_text(pdf_bytes, filename)
        
        # The key test is that pypdf was used instead of PyPDF2
        assert result == "PDF content"
        mock_reader.assert_called_once()
    
    def test_extract_pdf_text_encrypted_pdf(self, gmail_server):
        """Test PDF extraction with encrypted PDF."""
        pdf_bytes = b"encrypted_pdf_content"
        filename = "encrypted.pdf"
        
        with patch('gmail_server.pypdf.PdfReader') as mock_reader:
            mock_pdf_instance = Mock()
            mock_pdf_instance.is_encrypted = True
            mock_reader.return_value = mock_pdf_instance
            
            with patch('gmail_server.signal.signal'), \
                 patch('gmail_server.signal.alarm'):
                
                result = gmail_server._extract_pdf_text(pdf_bytes, filename)
        
        # Should return None for encrypted PDFs (with default skip setting)
        assert result is None
    
    def test_extract_pdf_text_error_handling(self, gmail_server):
        """Test PDF extraction error handling."""
        pdf_bytes = b"corrupted_pdf"
        filename = "corrupted.pdf"
        
        with patch('gmail_server.pypdf.PdfReader') as mock_reader:
            # Simulate pypdf error
            mock_reader.side_effect = Exception("Invalid PDF")
            
            with patch('gmail_server.signal.signal'), \
                 patch('gmail_server.signal.alarm'):
                
                result = gmail_server._extract_pdf_text(pdf_bytes, filename)
        
        # Should return None on error
        assert result is None
    
    def test_pypdf_replaced_pyPDF2(self):
        """Test that pypdf is used instead of deprecated PyPDF2."""
        # This test ensures we're using the modern pypdf library
        import gmail_server
        
        # Check that gmail_server uses pypdf (not PyPDF2)
        assert hasattr(gmail_server, 'pypdf'), "gmail_server should import pypdf"
        
        # Verify pypdf.PdfReader is available (the new API)
        with patch('gmail_server.pypdf.PdfReader') as mock_reader:
            mock_reader.return_value = Mock()
            # This confirms we can mock the new pypdf interface
            assert mock_reader is not None
    
    def test_pdf_processing_config_exists(self, gmail_server):
        """Test that PDF processing configuration exists."""
        config = gmail_server.config
        
        # Verify the config structure exists
        assert 'processing' in config
        assert 'pdf_processing' in config['processing']
        assert 'enabled' in config['processing']['pdf_processing']
        assert 'timeout_seconds' in config['processing']['pdf_processing']
        assert 'skip_password_protected' in config['processing']['pdf_processing']