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
                'business_domains': ['billing', 'noreply'],
                'prompt_template': '''You are an expert at identifying and extracting data from Swedish and English invoices in emails and PDF attachments.

Analyze this email (including any PDF attachment content) and determine:
1. Is this a legitimate invoice/bill (not promotional, not receipt, not notification)?
2. If yes, extract the following information:

Email Content:
{email_content}

Extract this information if it's an invoice:
- vendor: Company/organization name
- invoice_number: Invoice or reference number  
- amount: Total amount (just the number, no currency)
- currency: Currency (SEK, USD, EUR, etc.)
- due_date: Payment due date (YYYY-MM-DD format)
- invoice_date: Invoice date (YYYY-MM-DD format)
- ocr: OCR number (Swedish format, typically 16-20 digits)
- description: Brief description of what this is for

Swedish Invoice Patterns to Look For:
- Keywords: {swedish_keywords}
- Currency: kr, SEK, :-

English Invoice Patterns:
- Keywords: {english_keywords}
- Currency: $, €, SEK, etc.

Respond with ONLY a JSON object like this:
{{
    "is_invoice": true/false,
    "vendor": "vendor name",
    "invoice_number": "invoice number",
    "amount": "amount without currency",
    "currency": "SEK/USD/EUR",
    "due_date": "YYYY-MM-DD",
    "invoice_date": "YYYY-MM-DD", 
    "ocr": "OCR number if found",
    "description": "brief description",
    "confidence": 0.0-1.0
}}

If not an invoice, respond with: {{"is_invoice": false}}'''
            },
            'concerts': {
                'enabled': True,
                'output_file': 'output/concerts.csv',
                'keywords': {
                    'swedish': ['konsert', 'live'],
                    'english': ['concert', 'show']
                },
                'prompt_template': '''Extract concert information from this email content for concerts in Sweden.

Email content:
{email_content}

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

Return empty array [] if no concerts in Sweden found.'''
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