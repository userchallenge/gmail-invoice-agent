import argparse
import yaml
import os
import logging
from dotenv import load_dotenv
from agents.email_processor import EmailProcessor
from gmail_server import GmailServer
from csv_exporter import CSVExporter

logger = logging.getLogger(__name__)

def setup_logging(log_file: str = None):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()]
        )
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)

def main():
    # Load environment variables
    load_dotenv()
    
    parser = argparse.ArgumentParser(description='Gmail Invoice Extractor')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    parser.add_argument('--days-back', type=int, help='Number of days back to search', default=None)
    args = parser.parse_args()
    
    # Load configuration
    try:
        with open(args.config, 'r') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        return 1
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return 1
    
    # Force enable only invoices
    extractors_config = config.get('extractors', {})
    for name in extractors_config:
        extractors_config[name]['enabled'] = (name == 'invoices')
    
    # Override days back if specified
    if args.days_back:
        config['processing']['default_days_back'] = args.days_back
        logger.info(f"Using custom days back: {args.days_back}")
    
    # Setup logging
    if "log_file" in config["output"]:
        setup_logging(config["output"]["log_file"])
    else:
        setup_logging()
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        logger.error("CLAUDE_API_KEY not found in environment variables")
        logger.error("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1
    
    # Initialize components
    try:
        email_processor = EmailProcessor(config, claude_api_key)
        gmail_server = GmailServer(
            config['gmail']['credentials_file'],
            config['gmail']['token_file'],
            config['gmail']['scopes'],
            config
        )
        csv_exporter = CSVExporter()
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        return 1
    
    logger.info("=== Gmail Invoice Extractor ===")
    logger.info("🧾 Extracting invoice data only")
    
    try:
        if args.dummy_data:
            logger.info("Using dummy invoice data for testing...")
            return run_dummy_invoice_test(email_processor, csv_exporter, config)
        else:
            return run_invoice_extraction(email_processor, gmail_server, csv_exporter, config)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def run_invoice_extraction(email_processor, gmail_server, csv_exporter, config):
    """Run invoice extraction from Gmail"""
    # Get invoice keywords and filters only
    search_keywords = email_processor.get_search_keywords()
    search_filters = email_processor.get_search_filters()
    logger.info(f"Searching for invoice emails with {len(search_keywords)} keywords and {len(search_filters)} filters...")
    
    # Fetch emails
    days_back = config['processing']['default_days_back']
    emails = gmail_server.fetch_emails_for_extractors(search_keywords, search_filters, days_back)
    logger.info(f"Found {len(emails)} potential invoice emails")
    
    if not emails:
        logger.info("No emails found matching invoice criteria")
        return 0
    
    # Process emails
    invoice_results = []
    processed = 0
    
    for email in emails:
        try:
            email_content = gmail_server.get_email_content(email['id'])
            email_metadata = {
                'date': email.get('date', ''),
                'sender': email.get('sender', ''),
                'subject': email.get('subject', ''),
                'id': email['id'],
                'attachments': email.get('attachments', []),
                'pdf_processed': email.get('pdf_processed', False),
                'pdf_filename': email.get('pdf_filename', ''),
                'pdf_text': email.get('pdf_text', ''),
                'pdf_text_length': email.get('pdf_text_length', 0),
                'pdf_processing_error': email.get('pdf_processing_error', '')
            }
            
            results = email_processor.process_email(email_content, email_metadata)
            
            if 'invoices' in results:
                invoice_results.extend(results['invoices'])
                logger.info(f"✓ Found invoice in: {email_metadata['subject'][:50]}...")
            
            processed += 1
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(emails)} emails...")
            
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            continue
    
    # Export results
    if invoice_results:
        output_file = config['extractors']['invoices']['output_file']
        csv_exporter.export_extractor_data('invoices', invoice_results, output_file)
        
        # Show sample invoice details
        logger.info("\n🧾 INVOICES FOUND:")
        for i, invoice in enumerate(invoice_results[:5]):  # Show first 5
            vendor = invoice.get('vendor', 'Unknown Vendor')
            amount = invoice.get('amount', 'Unknown')
            currency = invoice.get('currency', 'SEK')
            due_date = invoice.get('due_date', 'Unknown')
            logger.info(f"   {i+1}. {vendor}: {amount} {currency} (due: {due_date})")
        
        if len(invoice_results) > 5:
            logger.info(f"   ... and {len(invoice_results) - 5} more")
    
    logger.info(f"\n📊 INVOICE SUMMARY: {len(invoice_results)} invoices from {processed} emails")
    
    if invoice_results:
        # Calculate totals by currency
        currency_totals = {}
        for invoice in invoice_results:
            currency = invoice.get('currency', 'SEK')
            try:
                amount = float(invoice.get('amount', 0))
                currency_totals[currency] = currency_totals.get(currency, 0) + amount
            except (ValueError, TypeError):
                continue
        
        if currency_totals:
            logger.info("💰 Total amounts:")
            for currency, total in currency_totals.items():
                logger.info(f"   {currency}: {total:.2f}")
    
    return 0

def run_dummy_invoice_test(email_processor, csv_exporter, config):
    """Run extraction with dummy invoice data for testing"""
    logger.info("Creating dummy invoice data for testing...")
    
    dummy_invoices = [
        {
            'email_id': 'dummy_invoice_001',
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
        },
        {
            'email_id': 'dummy_invoice_002',
            'email_subject': 'Vattenfall Elräkning',
            'email_sender': 'noreply@vattenfall.se',
            'email_date': '2025-01-10 08:15:00',
            'vendor': 'Vattenfall AB',
            'invoice_number': 'EL-2025-0145',
            'amount': '1250.50',
            'currency': 'SEK',
            'due_date': '2025-02-10',
            'invoice_date': '2025-01-10',
            'ocr': '123456789012345678',
            'description': 'Electricity bill January 2025',
            'confidence': 0.98,
            'processed_date': '2025-01-15 15:45:00',
            'pdf_processed': True,
            'pdf_filename': 'vattenfall_invoice.pdf',
            'pdf_text_length': 1500,
            'pdf_processing_error': ''
        }
    ]
    
    # Export dummy results
    output_file = config['extractors']['invoices']['output_file']
    csv_exporter.export_extractor_data('invoices', dummy_invoices, output_file)
    
    logger.info(f"✓ Created {len(dummy_invoices)} dummy invoices")
    logger.info("✓ Dummy invoice test completed successfully")
    return 0

if __name__ == "__main__":
    exit(main())