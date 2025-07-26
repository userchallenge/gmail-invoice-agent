#!/usr/bin/env python3
"""
Basic functionality test for Gmail Invoice Agent
Run this to verify everything is working before processing real emails
"""

import os
import sys
import yaml
import logging
from datetime import datetime
from dotenv import load_dotenv

# Import our modules
from gmail_server import GmailServer
from email_classifier import EmailClassifier  
from csv_exporter import CSVExporter

def test_config_loading():
    """Test configuration loading"""
    print("🧪 Testing configuration loading...")
    
    try:
        with open('config/config.yaml', 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        required_sections = ['claude', 'gmail', 'processing', 'output']
        for section in required_sections:
            assert section in config, f"Missing config section: {section}"
        
        # Check Claude API key is set in environment
        claude_key = os.getenv('CLAUDE_API_KEY')
        assert claude_key is not None, "CLAUDE_API_KEY environment variable not set"
        
        print("✅ Configuration loading: PASSED")
        return config
        
    except Exception as e:
        print(f"❌ Configuration loading: FAILED - {e}")
        return None

def test_gmail_credentials():
    """Test Gmail credentials file exists"""
    print("🧪 Testing Gmail credentials...")
    
    creds_file = 'config/gmail_credentials.json'
    
    if os.path.exists(creds_file):
        print("✅ Gmail credentials file: FOUND")
        return True
    else:
        print(f"❌ Gmail credentials file: NOT FOUND at {creds_file}")
        print("   Please download from Google Cloud Console")
        return False

def test_csv_exporter():
    """Test CSV export functionality with dummy data"""
    print("🧪 Testing CSV export...")
    
    try:
        # Create test data
        test_data = [
            {
                'email_id': 'test_001',
                'email_subject': 'Test Faktura från Vattenfall',
                'email_sender': 'noreply@vattenfall.se',
                'email_date': '2024-07-20 10:30:00',
                'vendor': 'Vattenfall',
                'invoice_number': 'INV-2024-001',
                'amount': '1250.50',
                'currency': 'SEK',
                'due_date': '2024-08-15',
                'invoice_date': '2024-07-15',
                'ocr': '12345678901234567890',
                'description': 'Electricity bill',
                'confidence': 0.95,
                'processed_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        ]
        
        # Test export
        exporter = CSVExporter('output/test_invoices.csv')
        success = exporter.export_invoices(test_data)
        
        if success and os.path.exists('output/test_invoices.csv'):
            print("✅ CSV export: PASSED")
            
            # Test stats
            stats = exporter.get_summary_stats()
            if stats:
                print(f"   • Total invoices: {stats.get('total_invoices', 0)}")
                print(f"   • Total amount: {stats.get('total_amount', 0):.2f} SEK")
            
            return True
        else:
            print("❌ CSV export: FAILED")
            return False
            
    except Exception as e:
        print(f"❌ CSV export: FAILED - {e}")
        return False

def test_email_classifier_init(config):
    """Test email classifier initialization"""
    print("🧪 Testing email classifier initialization...")
    
    try:
        classifier = EmailClassifier(
            api_key=os.getenv('CLAUDE_API_KEY'),
            config=config
        )
        
        # Test basic properties
        assert hasattr(classifier, 'client'), "Missing Claude client"
        assert hasattr(classifier, 'invoice_keywords'), "Missing invoice keywords"
        
        print("✅ Email classifier init: PASSED")
        return True
        
    except Exception as e:
        print(f"❌ Email classifier init: FAILED - {e}")
        return False

def test_dummy_email_processing(config):
    """Test processing with dummy email data"""
    print("🧪 Testing dummy email processing...")
    
    try:
        # Create dummy Swedish invoice email
        dummy_email = {
            'id': 'dummy_001',
            'subject': 'Faktura från Vattenfall - Förfallodag 2024-08-15',
            'sender': 'noreply@vattenfall.se',
            'date': '2024-07-20 10:30:00',
            'body': '''
            Hej,
            
            Din faktura från Vattenfall är nu tillgänglig.
            
            Fakturanummer: VF-2024-123456
            Totalt belopp: 1,250.50 kr
            Förfallodag: 2024-08-15
            OCR: 12345678901234567890
            
            Tack för att du är kund hos oss!
            
            Vattenfall
            ''',
            'attachments': [{'filename': 'faktura.pdf'}]
        }
        
        classifier = EmailClassifier(
            api_key=os.getenv('CLAUDE_API_KEY'),
            config=config
        )
        
        # Test basic invoice detection
        has_indicators = classifier._has_invoice_indicators(dummy_email)
        
        if has_indicators:
            print("✅ Invoice detection: PASSED")
            print("   • Found Swedish invoice keywords")
            return True
        else:
            print("❌ Invoice detection: FAILED")
            print("   • Swedish keywords not detected properly")
            return False
            
    except Exception as e:
        print(f"❌ Dummy email processing: FAILED - {e}")
        return False

def main():
    """Run all basic tests"""
    # Load environment variables from .env file
    load_dotenv()
    
    print("=" * 60)
    print("🧪 Gmail Invoice Agent - Basic Functionality Tests")
    print("=" * 60)
    print()
    
    # Setup logging
    logging.basicConfig(level=logging.WARNING)  # Suppress INFO logs during testing
    
    test_results = []
    
    # Test 1: Config loading
    config = test_config_loading()
    test_results.append(config is not None)
    
    if not config:
        print("\n❌ Cannot continue tests without valid configuration")
        sys.exit(1)
    
    print()
    
    # Test 2: Gmail credentials
    gmail_ok = test_gmail_credentials()
    test_results.append(gmail_ok)
    print()
    
    # Test 3: CSV export
    csv_ok = test_csv_exporter()
    test_results.append(csv_ok)
    print()
    
    # Test 4: Email classifier
    classifier_ok = test_email_classifier_init(config)
    test_results.append(classifier_ok)
    print()
    
    # Test 5: Dummy email processing
    dummy_ok = test_dummy_email_processing(config)
    test_results.append(dummy_ok)
    print()
    
    # Summary
    passed = sum(test_results)
    total = len(test_results)
    
    print("=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("🎉 All tests passed! System is ready for use.")
        print("\nNext steps:")
        print("1. Run: python demo.py --days-back 7 --verbose")
        print("2. Check output/invoices.csv for results")
    else:
        print("⚠️  Some tests failed. Please fix issues before proceeding.")
        
        if not gmail_ok:
            print("\n📝 To fix Gmail credentials:")
            print("1. Go to Google Cloud Console")
            print("2. Download OAuth credentials JSON")
            print("3. Save as config/gmail_credentials.json")
    
    print()

if __name__ == "__main__":
    main()