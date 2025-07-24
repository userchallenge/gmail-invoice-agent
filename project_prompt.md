Email-to-CSV AI Agent POC - Complete Implementation Guide
CRITICAL: This prompt is for an LLM to build working Python code
YOU MUST provide complete, executable code files that work together as a system. Include all imports, error handling, and configuration setup. Test with dummy data first, then provide clear instructions for Gmail API setup.

Project Overview
Create a proof-of-concept AI agent system that automatically processes personal Gmail emails to: 1) identify emails containing real invoices and extract payment-related data into CSV format, and 2) identify personal emails from friends and family, demonstrating intelligent email categorization and data extraction capabilities.

Business Context
Target Audience: CEO of small family business (demonstrating AI capabilities)
Use Case: Personal Gmail management and invoice processing
Current Process: Manual sorting of emails and invoice data entry
Goal: Demonstrate intelligent email categorization and automated data extraction
Timeline: 2 weeks (beginning August)
Technical Requirements
Architecture
LLM: Local model (e.g., Ollama with Llama 3.1 or similar)
MCP Servers: 1-2 maximum
Language: Python
Interface: Command line demonstration
Data: Dummy data acceptable
Core Components to Build
1. Email Classification Agent
Functionality:

Connect to Gmail via MCP server
Classify emails into categories: invoices, personal (friends/family), other
Extract payment data from invoice emails (amount, due date, vendor, invoice number)
Export invoice data to CSV format
Tag/organize personal emails from contacts
Invoice Data to Extract:

Vendor/company name
Invoice number
Amount due
Due date
Invoice date
OCR (Swedish invoice identifier)
Vendor contact info
Personal Email Identification:

Sender analysis (friends/family vs business)
Content pattern recognition
Contact relationship mapping
2. MCP Servers (Choose 1-2)
Option A: Gmail MCP Server

Connect to Gmail API for email access
Provide methods: fetch_emails(), get_email_content(), update_labels()
Handle authentication and rate limiting
Option B: CSV Export MCP Server

Generate structured CSV files from extracted data
Methods: create_invoice_csv(), append_invoice_data(), export_contacts()
File management and data formatting
Implementation Structure
IMPORTANT: Provide complete working code for each file below

gmail-invoice-agent/
├── agents/
│   └── email_classifier.py        # Complete AI agent implementation
├── mcp_servers/
│   ├── gmail_server.py            # Full Gmail API integration with auth
│   └── csv_export_server.py       # Complete CSV operations
├── tests/                         # Complete pytest test suite
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures and configuration
│   ├── test_email_classifier.py   # Unit tests for AI agent
│   ├── test_gmail_server.py       # Gmail API tests with mocking
│   ├── test_csv_export.py         # CSV operations tests
│   ├── test_integration.py        # End-to-end integration tests
│   └── fixtures/                  # Test data
│       ├── sample_invoices.json   # Invoice email examples
│       ├── sample_personal.json   # Personal email examples
│       └── expected_outputs.json  # Expected classification results
├── config/
│   ├── config.yaml                # All configuration parameters
│   └── gmail_credentials.json     # Template for Gmail API setup
├── output/                        # Auto-created by script
│   ├── invoices.csv               # Generated invoice data
│   └── personal_contacts.csv      # Generated personal email data
├── demo.py                        # Complete runnable demonstration
├── requirements.txt               # All Python dependencies
├── setup_instructions.md          # Step-by-step setup guide
└── README.md                      # Usage instructions
CODE REQUIREMENTS:

Every .py file must be complete and executable
Include all necessary imports and dependencies
Add comprehensive error handling
Provide fallback dummy data if Gmail API fails
Include logging for debugging
Add configuration validation
Key Features to Demonstrate
1. Intelligent Email Classification
Automatically categorize emails (invoice, personal, promotional, etc.)
Extract structured data from unstructured invoice content
Confidence scoring for classifications
2. Invoice Data Extraction
Parse various invoice formats (PDF attachments, HTML emails, plain text)
Normalize payment data across different vendors
Handle multiple currencies and date formats
3. Personal Contact Management
Identify friends/family based on email patterns and content
Build relationship mapping over time
Separate personal from business communications
CRITICAL SUCCESS REQUIREMENTS
1. Complete requirements.txt with exact versions:

anthropic>=0.25.0
google-auth>=2.22.0
google-auth-oauthlib>=1.0.0
google-auth-httplib2>=0.1.0
google-api-python-client>=2.100.0
pyyaml>=6.0
pandas>=2.0.0
python-dateutil>=2.8.0
tqdm>=4.65.0
pytest>=7.4.0
pytest-mock>=3.11.0
pytest-cov>=4.1.0
responses>=0.23.0
2. Working config.yaml template:

yaml
# Complete configuration with all required parameters
claude:
  api_key: "your-claude-api-key-here"
  model: "claude-3-sonnet-20240229"

gmail:
  credentials_file: "config/gmail_credentials.json"
  token_file: "config/gmail_token.json"
  scopes: ["https://www.googleapis.com/auth/gmail.readonly"]

processing:
  default_days_back: 30
  max_emails: 100
  batch_size: 10

# Invoice identification keywords (English/Swedish)
invoice_keywords:
  invoice_indicators:
    english: ["invoice", "bill", "statement", "due", "payment due", "amount due", "total amount"]
    swedish: ["faktura", "räkning", "förfallodag", "förfallodatum", "betalning", "att betala", "totalt belopp"]
  
  vendor_identifiers:
    english: ["from:", "invoice from", "bill from", "statement from"]
    swedish: ["från:", "faktura från", "räkning från"]
    
  amount_patterns:
    english: ["total:", "amount:", "due:", "balance:", "pay:", "SEK", "kr", "$", "€"]
    swedish: ["totalt:", "belopp:", "att betala:", "saldo:", "kr", "SEK", ":-"]
    
  date_patterns:
    english: ["due date:", "payment due:", "due by:", "pay by:"]
    swedish: ["förfallodag:", "förfallodatum:", "betalas senast:", "betala före:"]

# Personal contacts configuration
personal_contacts:
  # Known friends/family (configure these)
  known_contacts:
    - email: "friend1@example.com"
      name: "John Smith"
      relationship: "friend"
    - email: "sister@example.com"
      name: "Anna Johnson"
      relationship: "family"
    - email: "mom@example.com"
      name: "Mom"
      relationship: "family"
  
  # Domain patterns for personal emails
  personal_domains:
    - "gmail.com"
    - "hotmail.com"
    - "yahoo.com"
    - "protonmail.com"
  
  # Exclude business domains
  business_domains:
    - "noreply"
    - "no-reply"
    - "support"
    - "billing"
    - "invoice"
    - "automated"

output:
  invoices_file: "output/invoices.csv"
  contacts_file: "output/personal_contacts.csv"
3. Dummy data fallback for testing:

Must work even without Gmail API access
Include realistic Swedish invoice examples
Demonstrate all features with sample data
4. Swedish Invoice Recognition:

OCR format: typically 16-20 digit numeric string
Common Swedish vendors: "Vattenfall", "Telia", "ICA", "Coop"
Handle Swedish characters (å, ä, ö) in vendor names
Swedish date formats (YYYY-MM-DD)
5. Error Handling Requirements:

Gmail API rate limiting
Invalid credentials
Network failures
Missing email content
Unparseable invoice data
Invalid OCR formats
COMPREHENSIVE PYTEST TEST SUITE REQUIRED
MUST PROVIDE COMPLETE TEST FILES:

1. conftest.py - Shared fixtures
python
# EXACT implementation required:
import pytest
import json
from unittest.mock import Mock, patch
from agents.email_classifier import EmailClassifier
from mcp_servers.gmail_server import GmailServer

@pytest.fixture
def sample_invoice_email():
    # Real Swedish invoice email example
    pass

@pytest.fixture
def sample_personal_email():
    # Personal email from friend/family
    pass

@pytest.fixture
def mock_claude_client():
    # Mock anthropic client
    pass

@pytest.fixture
def mock_gmail_service():
    # Mock Gmail API service
    pass
2. test_email_classifier.py - Core AI functionality
python
# MUST TEST:
# - Invoice vs personal classification accuracy
# - Swedish OCR extraction from various formats
# - Configurable keyword matching (English/Swedish)
# - Personal contact identification from config
# - Domain-based classification logic
# - Business email exclusion patterns
# - Invalid email handling
# - Confidence scoring
# - Swedish vendor name recognition
# - Date parsing (Swedish formats)
# - Amount extraction with Swedish currency

class TestEmailClassifier:
    def test_classify_invoice_email_english(self, sample_invoice_email, mock_claude_client):
        # Test English invoice detection using configured keywords
        pass
        
    def test_classify_invoice_email_swedish(self, sample_swedish_invoice, mock_claude_client):
        # Test Swedish invoice detection using configured keywords
        pass
        
    def test_personal_contact_from_config(self, sample_personal_email, mock_claude_client):
        # Test personal email identification using configured contacts
        pass
        
    def test_domain_based_classification(self, mock_claude_client):
        # Test personal vs business domain classification
        pass
        
    def test_business_email_exclusion(self, mock_claude_client):
        # Test exclusion of noreply, support, billing emails
        pass
        
    def test_keyword_matching_bilingual(self, mock_claude_client):
        # Test both English and Swedish keyword recognition
        pass
        
    def test_extract_swedish_ocr(self, mock_claude_client):
        # Test OCR extraction from various Swedish invoice formats
        pass
        
    def test_invalid_email_handling(self, mock_claude_client):
        # Test graceful handling of malformed emails
        pass
3. test_gmail_server.py - Gmail API integration
python
# MUST TEST:
# - Authentication flow
# - Email fetching with date ranges
# - Rate limiting handling
# - Network error recovery
# - Email content parsing (HTML/plain text)
# - Attachment handling

class TestGmailServer:
    @patch('googleapiclient.discovery.build')
    def test_fetch_emails_success(self, mock_build, mock_gmail_service):
        # Test successful email fetching
        pass
        
    def test_fetch_emails_rate_limit(self, mock_gmail_service):
        # Test rate limiting scenarios
        pass
        
    def test_authentication_failure(self):
        # Test invalid credentials handling
        pass
4. test_csv_export.py - File operations
python
# MUST TEST:
# - CSV file creation with correct headers
# - Swedish character encoding (å, ä, ö)
# - Data validation before export
# - File overwriting behavior
# - Empty data handling

class TestCSVExporter:
    def test_create_invoice_csv(self, tmp_path):
        # Test invoice CSV generation with correct format
        pass
        
    def test_swedish_characters_encoding(self, tmp_path):
        # Test proper encoding of Swedish characters
        pass
        
    def test_append_invoice_data(self, tmp_path):
        # Test appending new invoice data
        pass
5. test_integration.py - End-to-end tests
python
# MUST TEST:
# - Complete workflow from email to CSV
# - Configuration loading
# - Error propagation
# - Output file validation
# - Performance with multiple emails

class TestIntegration:
    def test_complete_workflow_dummy_data(self, tmp_path):
        # Test full pipeline with dummy data
        pass
        
    def test_configuration_validation(self):
        # Test config loading and validation
        pass
        
    def test_output_file_format(self, tmp_path):
        # Validate CSV output matches exact specification
        pass
TEST DATA REQUIREMENTS:

At least 5 different Swedish invoice formats with Swedish keywords
At least 5 different English invoice formats with English keywords
Various personal email styles from configured contacts
Business emails that should be excluded (noreply, support, billing)
Edge cases (malformed emails, missing data, mixed languages)
Swedish vendor names with special characters
Different OCR formats and lengths
Test emails from both personal and business domains
Example Test Data Structure:

json
// tests/fixtures/sample_invoices.json
{
  "swedish_invoices": [
    {
      "subject": "Faktura från Vattenfall",
      "content": "Förfallodag: 2024-08-15\nTotalt belopp: 1250 kr\nOCR: 12345678901234567890",
      "expected": {
        "classification": "invoice",
        "vendor": "Vattenfall",
        "amount": "1250",
        "due_date": "2024-08-15",
        "ocr": "12345678901234567890"
      }
    }
  ],
  "english_invoices": [
    {
      "subject": "Invoice from Electric Company",
      "content": "Due Date: 2024-08-15\nTotal Amount: $125.50\nInvoice #: INV-2024-001",
      "expected": {
        "classification": "invoice",
        "vendor": "Electric Company",
        "amount": "125.50",
        "due_date": "2024-08-15"
      }
    }
  ]
}
PYTEST CONFIGURATION:

ini
# pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = --cov=agents --cov=mcp_servers --cov-report=html --cov-report=term-missing
Demo Script Flow
Demo Script - EXACT IMPLEMENTATION REQUIRED
python
# demo.py - Must be completely runnable with: python demo.py
import argparse
import yaml
from agents.email_classifier import EmailClassifier
from mcp_servers.gmail_server import GmailServer
from mcp_servers.csv_export_server import CSVExporter

def main():
    # MUST include:
    # - Argument parsing for date range (but default to config file setting)
    # - Configuration loading from YAML with keyword validation
    # - Personal contacts loading and validation
    # - Error handling for API failures
    # - Progress bars/logging for user feedback
    # - Fallback to dummy data if needed
    # - Clear summary statistics at end
    # - Bilingual processing demonstration (English/Swedish)
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    # Note: date range comes from config file, not command line
    # ... complete implementation required
    
if __name__ == "__main__":
    main()
Success Metrics to Display
Processing Efficiency:

Manual invoice data entry: ~3-5 minutes per invoice
Automated extraction: ~10 seconds per invoice
Manual email sorting: ~1 minute per email
Automated classification: ~2 seconds per email
Data Quality:

Invoice data extraction accuracy: X/Y (Z%)
Email classification accuracy: A/B (C%)
Personal contact identification rate: D/E (F%)
Practical Value:

Monthly invoices processed automatically
Personal emails properly categorized
Structured data ready for accounting software import
Technical Implementation Notes
Claude API Integration
python
# EXACT code structure to implement:
import anthropic
import os
from typing import Dict, List, Optional

class EmailClassifier:
    def __init__(self, api_key: str, config: Dict):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.invoice_keywords = config['invoice_keywords']
        self.personal_contacts = config['personal_contacts']
        
    def classify_email(self, email_content: str, sender: str) -> Dict:
        # Must use configurable keywords for classification
        # Check against known personal contacts first
        # Use both English and Swedish keyword matching
        pass
        
    def extract_invoice_data(self, email_content: str) -> Optional[Dict]:
        # Must extract: vendor, invoice_number, amount, due_date, invoice_date, ocr
        # Use configured keywords for field identification
        # Handle both English and Swedish formats
        # Use keyword patterns from config for better accuracy
        pass
        
    def is_personal_contact(self, sender_email: str, sender_name: str) -> bool:
        # Check against configured personal contacts
        # Check domain patterns for personal vs business
        # Exclude business automation patterns
        pass
Gmail Integration - COMPLETE WORKING CODE REQUIRED
python
# Template for gmail_server.py - MUST BE FULLY IMPLEMENTED
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import email
from datetime import datetime, timedelta

class GmailServer:
    def __init__(self, credentials_file: str, token_file: str):
        # Complete authentication setup
        pass
        
    def fetch_emails(self, days_back: int = 30) -> List[Dict]:
        # Must return structured email data
        pass
        
    def get_email_content(self, email_id: str) -> str:
        # Handle both plain text and HTML
        pass
CSV Export - EXACT FORMAT REQUIRED
python
# csv_export_server.py must create files with these exact headers:
# invoices.csv: vendor,invoice_number,amount,due_date,invoice_date,ocr,email_date
# personal_contacts.csv: sender_name,sender_email,relationship,email_count,last_contact
DELIVERABLES - ALL MUST BE PROVIDED
1. Complete Working Code Files:

demo.py (fully executable)
agents/email_classifier.py (complete implementation)
mcp_servers/gmail_server.py (with authentication)
mcp_servers/csv_export_server.py (with file operations)
config/config.yaml (working template)
requirements.txt (tested dependencies)
2. Complete Pytest Test Suite:

tests/conftest.py (shared fixtures)
tests/test_email_classifier.py (AI functionality tests)
tests/test_gmail_server.py (Gmail API tests with mocking)
tests/test_csv_export.py (CSV operations tests)
tests/test_integration.py (end-to-end workflow tests)
tests/fixtures/ (sample data for testing)
pytest.ini (test configuration)
3. Setup Documentation:

setup_instructions.md with Gmail API setup steps
README.md with usage examples and testing instructions
Sample output files showing expected format
Business Value Demonstration
For CEO Presentation:

Clear demonstration of AI email processing capabilities
Quantified productivity improvements
Personal data organization benefits
Scalability to business email processing
Key Messages:

"This system can process and categorize 100 emails in minutes"
"Automatically extracts invoice data for accounting"
"Intelligently identifies personal vs business communications"
"Demonstrates AI potential for business email automation"
IMMEDIATE DEVELOPMENT TASKS
PROVIDE COMPLETE CODE FOR:

demo.py - Must run immediately with dummy data
config/config.yaml - Working configuration template
requirements.txt - All dependencies with versions
agents/email_classifier.py - Complete Claude API integration
mcp_servers/gmail_server.py - Full Gmail API handling
mcp_servers/csv_export_server.py - CSV file operations
Complete pytest test suite - All test files with real test cases
setup_instructions.md - Step-by-step Gmail API setup
VALIDATION CHECKLIST:

 Code runs without errors using dummy data
 All imports resolve correctly
 Configuration loads properly
 CSV files generate with correct headers
 Error handling prevents crashes
 Clear user feedback during processing
 Gmail API integration ready for credentials
 All tests pass with pytest tests/
 Test coverage above 80%
 Tests work without external API calls (mocked)
TESTING PRIORITY:

First: All tests pass with mocked APIs
Second: Dummy data mode (no external APIs)
Third: Claude API integration with sample emails
Fourth: Gmail API integration with real emails
TEST EXECUTION:

bash
# Must work immediately:
pip install -r requirements.txt
pytest tests/ -v --cov
python demo.py --dummy-data  # Run with test data first
Questions for Implementation
Any specific Swedish invoice formats or vendors you commonly receive that should be prioritized for testing?
Should the system handle both Swedish and English language invoices?
Any particular friends/family email patterns that would be good test cases?
Preferred date range configuration method (config file, command line parameter, or both)?
