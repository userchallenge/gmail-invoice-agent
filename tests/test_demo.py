"""Integration tests for the demo.py script."""

import pytest
import tempfile
import os
import sys
from unittest.mock import Mock, patch
from io import StringIO

# Add the parent directory to the path so we can import demo
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import demo


class TestDemoScript:
    """Test cases for the demo.py script."""
    
    @pytest.fixture
    def mock_components(self):
        """Mock the main components used by demo.py."""
        with patch('demo.EmailProcessor') as mock_email_processor, \
             patch('demo.GmailServer') as mock_gmail_server, \
             patch('demo.CSVExporter') as mock_csv_exporter:
            
            # Setup EmailProcessor mock
            mock_email_processor_instance = Mock()
            mock_email_processor_instance.get_enabled_extractors.return_value = ['invoices']
            mock_email_processor_instance.get_extractor_output_files.return_value = {'invoices': 'output/invoices.csv'}
            
            # Setup mock extractor for new separate search functionality
            mock_extractor = Mock()
            mock_extractor.get_search_keywords.return_value = ['invoice', 'faktura']
            mock_extractor.get_additional_search_filters.return_value = []
            mock_extractor.extract.return_value = [{'test': 'data'}]
            mock_email_processor_instance.get_extractor_by_name.return_value = mock_extractor
            
            mock_email_processor.return_value = mock_email_processor_instance
            
            # Setup GmailServer mock
            mock_gmail_server_instance = Mock()
            mock_gmail_server_instance.fetch_emails_for_extractors.return_value = [{
                'id': 'test_email_001',
                'subject': 'Test Email',
                'sender': 'test@example.com',
                'date': '2025-01-15 12:00:00',
                'attachments': []
            }]
            mock_gmail_server_instance.get_email_content.return_value = 'Test email content'
            mock_gmail_server.return_value = mock_gmail_server_instance
            
            # Setup CSVExporter mock
            mock_csv_exporter_instance = Mock()
            mock_csv_exporter.return_value = mock_csv_exporter_instance
            
            yield {
                'email_processor': mock_email_processor,
                'gmail_server': mock_gmail_server,
                'csv_exporter': mock_csv_exporter,
                'email_processor_instance': mock_email_processor_instance,
                'gmail_server_instance': mock_gmail_server_instance,
                'csv_exporter_instance': mock_csv_exporter_instance,
                'mock_extractor': mock_extractor
            }
    
    def test_setup_logging_with_file(self, temp_output_dir):
        """Test setup_logging function with file output."""
        log_file = os.path.join(temp_output_dir, 'test.log')
        
        # This should not raise any exceptions
        demo.setup_logging(log_file)
        
        # Check that the log file directory was created
        assert os.path.exists(os.path.dirname(log_file))
    
    def test_setup_logging_without_file(self):
        """Test setup_logging function without file output."""
        # This should not raise any exceptions
        demo.setup_logging()
    
    @patch.dict('os.environ', {'CLAUDE_API_KEY': 'test-key'})
    @patch('demo.load_dotenv')
    @patch('builtins.open')
    @patch('demo.yaml.safe_load')
    def test_main_with_dummy_data_invoices_only(self, mock_yaml_load, mock_open, mock_load_dotenv, mock_components, sample_config):
        """Test main function with dummy data and invoices only."""
        # Setup mocks
        mock_yaml_load.return_value = sample_config
        mock_components['email_processor_instance'].get_enabled_extractors.return_value = ['invoices']
        
        # Mock sys.argv
        test_args = ['demo.py', '--extractors', 'invoices', '--dummy-data']
        
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new_callable=StringIO):
                result = demo.main()
        
        assert result == 0
        mock_components['email_processor'].assert_called_once()
        mock_components['gmail_server'].assert_called_once()
        mock_components['csv_exporter'].assert_called_once()
    
    @patch.dict('os.environ', {'CLAUDE_API_KEY': 'test-key'})
    @patch('demo.load_dotenv')
    @patch('builtins.open')
    @patch('demo.yaml.safe_load')
    def test_main_with_dummy_data_concerts_only(self, mock_yaml_load, mock_open, mock_load_dotenv, mock_components, sample_config):
        """Test main function with dummy data and concerts only."""
        # Setup mocks
        mock_yaml_load.return_value = sample_config
        mock_components['email_processor_instance'].get_enabled_extractors.return_value = ['concerts']
        mock_components['email_processor_instance'].get_extractor_output_files.return_value = {'concerts': 'output/concerts.csv'}
        
        # Mock sys.argv
        test_args = ['demo.py', '--extractors', 'concerts', '--dummy-data']
        
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new_callable=StringIO):
                result = demo.main()
        
        assert result == 0
        mock_components['email_processor'].assert_called_once()
    
    @patch.dict('os.environ', {'CLAUDE_API_KEY': 'test-key'})
    @patch('demo.load_dotenv')
    @patch('builtins.open')
    @patch('demo.yaml.safe_load')
    def test_main_with_all_extractors(self, mock_yaml_load, mock_open, mock_load_dotenv, mock_components, sample_config):
        """Test main function with all extractors."""
        # Setup mocks
        mock_yaml_load.return_value = sample_config
        mock_components['email_processor_instance'].get_enabled_extractors.return_value = ['invoices', 'concerts']
        mock_components['email_processor_instance'].get_extractor_output_files.return_value = {
            'invoices': 'output/invoices.csv',
            'concerts': 'output/concerts.csv'
        }
        
        # Mock sys.argv
        test_args = ['demo.py', '--extractors', 'all', '--dummy-data']
        
        with patch('sys.argv', test_args):
            with patch('sys.stdout', new_callable=StringIO):
                result = demo.main()
        
        assert result == 0
    
    @patch('demo.load_dotenv')
    @patch('builtins.open')
    @patch('demo.yaml.safe_load')
    def test_main_missing_claude_api_key(self, mock_yaml_load, mock_open, mock_load_dotenv, sample_config):
        """Test main function when CLAUDE_API_KEY is missing."""
        # Setup mocks
        mock_yaml_load.return_value = sample_config
        
        # Ensure CLAUDE_API_KEY is not set
        with patch.dict('os.environ', {}, clear=True):
            test_args = ['demo.py', '--dummy-data']
            
            with patch('sys.argv', test_args):
                with patch('sys.stdout', new_callable=StringIO):
                    result = demo.main()
        
        assert result == 1  # Should return error code
    
    def test_run_dummy_data_test_invoices(self, mock_components, sample_config):
        """Test run_dummy_data_test function with invoices."""
        # Setup mocks
        mock_email_processor = mock_components['email_processor_instance']
        mock_csv_exporter = mock_components['csv_exporter_instance']
        
        mock_email_processor.get_enabled_extractors.return_value = ['invoices']
        mock_email_processor.get_extractor_output_files.return_value = {'invoices': 'output/invoices.csv'}
        
        result = demo.run_dummy_data_test(mock_email_processor, mock_csv_exporter, sample_config)
        
        assert result == 0
        mock_csv_exporter.export_extractor_data.assert_called()
    
    def test_run_dummy_data_test_concerts(self, mock_components, sample_config):
        """Test run_dummy_data_test function with concerts."""
        # Setup mocks
        mock_email_processor = mock_components['email_processor_instance']
        mock_csv_exporter = mock_components['csv_exporter_instance']
        
        mock_email_processor.get_enabled_extractors.return_value = ['concerts']
        mock_email_processor.get_extractor_output_files.return_value = {'concerts': 'output/concerts.csv'}
        
        result = demo.run_dummy_data_test(mock_email_processor, mock_csv_exporter, sample_config)
        
        assert result == 0
        mock_csv_exporter.export_extractor_data.assert_called()
    
    def test_run_gmail_extraction_separate_searches(self, mock_components, sample_config):
        """Test run_gmail_extraction function with separate searches per extractor."""
        # Setup mocks for multiple extractors
        mock_email_processor = mock_components['email_processor_instance']
        mock_gmail_server = mock_components['gmail_server_instance']
        mock_csv_exporter = mock_components['csv_exporter_instance']
        
        # Mock enabled extractors
        mock_email_processor.get_enabled_extractors.return_value = ['invoices', 'concerts']
        mock_email_processor.get_extractor_output_files.return_value = {
            'invoices': 'output/invoices.csv',
            'concerts': 'output/concerts.csv'
        }
        
        # Mock different extractors with different search criteria
        invoice_extractor = Mock()
        invoice_extractor.get_search_keywords.return_value = ['invoice', 'faktura']
        invoice_extractor.get_additional_search_filters.return_value = []
        invoice_extractor.extract.return_value = [{'vendor': 'Test Vendor'}]
        
        concert_extractor = Mock()
        concert_extractor.get_search_keywords.return_value = ['concert', 'konsert']
        concert_extractor.get_additional_search_filters.return_value = []
        concert_extractor.extract.return_value = [{'artist': 'Test Artist'}]
        
        # Mock get_extractor_by_name to return different extractors
        def mock_get_extractor_by_name(name):
            if name == 'invoices':
                return invoice_extractor
            elif name == 'concerts':
                return concert_extractor
            return None
        
        mock_email_processor.get_extractor_by_name.side_effect = mock_get_extractor_by_name
        
        # Mock Gmail server to return different emails for different searches
        mock_gmail_server.fetch_emails_for_extractors.return_value = [{
            'id': 'test_email_001',
            'subject': 'Test Email',
            'sender': 'test@example.com',
            'date': '2025-01-15 12:00:00'
        }]
        mock_gmail_server.get_email_content.return_value = 'Test email content'
        
        with patch('sys.stdout', new_callable=StringIO):
            result = demo.run_gmail_extraction(mock_email_processor, mock_gmail_server, mock_csv_exporter, sample_config)
        
        assert result == 0
        # Verify that fetch_emails_for_extractors was called for each extractor
        assert mock_gmail_server.fetch_emails_for_extractors.call_count == 2
        # Verify that CSV export was called for each extractor
        assert mock_csv_exporter.export_extractor_data.call_count == 2