"""Pytest configuration and fixtures for Gmail Invoice Agent tests."""

import pytest
import yaml
import tempfile
import os
from unittest.mock import Mock
from datetime import datetime

# Test fixtures for dummy data
@pytest.fixture
def sample_invoice_data():
    """Sample invoice data for testing."""
    return {
        'email_id': 'test_invoice_001',
        'email_subject': 'Test Invoice from Anthropic',
        'email_sender': 'billing@anthropic.com',
        'email_date': '2025-01-15 10:30:00',
        'vendor': 'Anthropic, PBC',
        'invoice_number': 'INV-2025-001',
        'amount': '25.00',
        'currency': 'USD',
        'due_date': '2025-02-15',
        'invoice_date': '2025-01-15',
        'ocr': '',
        'description': 'Claude API usage',
        'confidence': 0.95,
        'processed_date': '2025-01-15 15:45:00',
        'pdf_processed': False,
        'pdf_filename': '',
        'pdf_text_length': 0,
        'pdf_processing_error': ''
    }

@pytest.fixture
def sample_concert_data():
    """Sample concert data for testing."""
    return {
        'artist': 'Test Band',
        'venue': 'Nalen',
        'town': 'Stockholm',
        'date': '2025-03-15',
        'room': 'Stora Salen',
        'ticket_info': 'Tickets available at venue',
        'email_date': '2025-01-15 12:00:00',
        'source_sender': 'info@nalen.se',
        'source_subject': 'Upcoming Concert: Test Band at Nalen',
        'email_id': 'test_concert_001',
        'processed_date': '2025-01-15 15:45:00'
    }

@pytest.fixture
def sample_config():
    """Sample configuration for testing."""
    return {
        'gmail': {
            'credentials_file': 'config/gmail_credentials.json',
            'token_file': 'config/gmail_token.json',
            'scopes': ['https://www.googleapis.com/auth/gmail.readonly']
        },
        'claude': {
            'model': 'claude-3-5-sonnet-20241022'
        },
        'processing': {
            'default_days_back': 30,
            'max_emails': 100,
            'batch_size': 10,
            'pdf_processing': {
                'enabled': True,
                'max_pdf_size_mb': 10,
                'timeout_seconds': 30,
                'skip_password_protected': True
            }
        },
        'extractors': {
            'invoices': {
                'enabled': True,
                'output_file': 'output/invoices.csv',
                'keywords': {
                    'swedish': ['faktura', 'räkning'],
                    'english': ['invoice', 'bill']
                },
                'business_domains': ['billing', 'noreply']
            },
            'concerts': {
                'enabled': True,
                'output_file': 'output/concerts.csv',
                'keywords': {
                    'swedish': ['konsert', 'live'],
                    'english': ['concert', 'show']
                }
            }
        },
        'output': {
            'directory': 'output/',
            'log_file': 'output/processing.log'
        }
    }

@pytest.fixture
def mock_claude_client():
    """Mock Claude client for testing."""
    mock_client = Mock()
    mock_response = Mock()
    mock_content = Mock()
    mock_content.text = '{"is_invoice": true, "vendor": "Test Vendor"}'
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response
    return mock_client

@pytest.fixture
def sample_email_metadata():
    """Sample email metadata for testing."""
    return {
        'id': 'test_email_001',
        'subject': 'Test Email Subject',
        'sender': 'test@example.com',
        'date': '2025-01-15 12:00:00',
        'attachments': [],
        'pdf_processed': False,
        'pdf_filename': '',
        'pdf_text': '',
        'pdf_text_length': 0,
        'pdf_processing_error': ''
    }

@pytest.fixture
def temp_output_dir():
    """Temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir

@pytest.fixture 
def config_file(sample_config, temp_output_dir):
    """Temporary config file for testing."""
    config_path = os.path.join(temp_output_dir, 'test_config.yaml')
    with open(config_path, 'w') as f:
        yaml.dump(sample_config, f)
    yield config_path