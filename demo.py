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
    
    parser = argparse.ArgumentParser(description='Gmail Multi-Purpose Email Extractor')
    parser.add_argument('--config', default='config/config.yaml', help='Config file path')
    parser.add_argument('--dummy-data', action='store_true', help='Use test data instead of Gmail API')
    parser.add_argument('--extractors', nargs='+', help='Specific extractors to run (invoices, concerts)', default=None)
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
    
    # Get Claude API key from environment
    claude_api_key = os.getenv('CLAUDE_API_KEY')
    if not claude_api_key:
        logger.error("CLAUDE_API_KEY not found in environment variables")
        logger.error("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1
    
    # Override extractor selection if specified
    if args.extractors:
        logger.info(f"Running only specified extractors: {args.extractors}")
        extractors_config = config.get('extractors', {})
        # Disable all extractors first
        for name in extractors_config:
            extractors_config[name]['enabled'] = False
        # Enable only specified ones
        for name in args.extractors:
            if name in extractors_config:
                extractors_config[name]['enabled'] = True
            else:
                logger.warning(f"Unknown extractor '{name}' - available: {list(extractors_config.keys())}")
    
    # Override days back if specified
    if args.days_back:
        config['processing']['default_days_back'] = args.days_back
        logger.info(f"Using custom days back: {args.days_back}")
    
    # Setup logging
    if "log_file" in config["output"]:
        setup_logging(config["output"]["log_file"])
    else:
        setup_logging()
    
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
    
    logger.info("=== Gmail Multi-Purpose Email Extractor ===")
    enabled_extractors = email_processor.get_enabled_extractors()
    if not enabled_extractors:
        logger.error("No extractors enabled! Check your config.yaml")
        return 1
    logger.info(f"Enabled extractors: {', '.join(enabled_extractors)}")
    
    try:
        if args.dummy_data:
            logger.info("Using dummy data for testing...")
            return run_dummy_data_test(email_processor, csv_exporter, config)
        else:
            return run_gmail_extraction(email_processor, gmail_server, csv_exporter, config)
                
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

def run_gmail_extraction(email_processor, gmail_server, csv_exporter, config):
    """Run extraction from Gmail"""
    # Get search keywords and filters from all enabled extractors
    search_keywords = email_processor.get_search_keywords()
    search_filters = email_processor.get_search_filters()
    logger.info(f"Searching for emails with {len(search_keywords)} keywords and {len(search_filters)} filters from all extractors")
    logger.debug(f"Keywords: {search_keywords[:10]}...")  # Show first 10
    logger.debug(f"Filters: {search_filters}")
    
    # Fetch emails
    days_back = config['processing']['default_days_back']
    emails = gmail_server.fetch_emails_for_extractors(search_keywords, search_filters, days_back)
    logger.info(f"Found {len(emails)} emails to process")
    
    if not emails:
        logger.info("No emails found matching criteria")
        return 0
    
    # Process emails through all extractors
    all_results = {}
    processed_count = 0
    
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
            
            # Collect results by extractor type
            for extractor_name, items in results.items():
                if extractor_name not in all_results:
                    all_results[extractor_name] = []
                all_results[extractor_name].extend(items)
            
            processed_count += 1
            if processed_count % 10 == 0:
                logger.info(f"Processed {processed_count}/{len(emails)} emails...")
                
        except Exception as e:
            logger.error(f"Error processing email {email['id']}: {e}")
            continue
    
    # Export results for each extractor
    extractor_output_files = email_processor.get_extractor_output_files()
    for extractor_name, items in all_results.items():
        if extractor_name in extractor_output_files:
            output_file = extractor_output_files[extractor_name]
            csv_exporter.export_extractor_data(extractor_name, items, output_file)
    
    # Summary statistics
    logger.info("\n=== EXTRACTION SUMMARY ===")
    total_items = 0
    for extractor_name, items in all_results.items():
        count = len(items)
        total_items += count
        logger.info(f"📊 {extractor_name.title()}: {count} items extracted")
    
    logger.info(f"📈 Total: {total_items} items from {processed_count} emails")
    
    # Show sample results for each extractor
    for extractor_name, items in all_results.items():
        if items:
            logger.info(f"\n📄 Sample {extractor_name} data:")
            sample_item = items[0]
            for key, value in list(sample_item.items())[:5]:  # Show first 5 fields
                logger.info(f"   {key}: {str(value)[:50]}...")
    
    return 0

def run_dummy_data_test(email_processor, csv_exporter, config):
    """Run extraction with dummy data for testing"""
    logger.info("Dummy data testing - creating sample data for enabled extractors")
    
    enabled_extractors = email_processor.get_enabled_extractors()
    dummy_results = {}
    
    # Create dummy invoice data if invoices extractor is enabled
    if 'invoices' in enabled_extractors:
        dummy_results['invoices'] = [{
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
        }]
    
    # Create dummy concert data if concerts extractor is enabled
    if 'concerts' in enabled_extractors:
        dummy_results['concerts'] = [{
            'artist': 'Test Band',
            'venue': 'Nalen',
            'town': 'Stockholm',
            'date': '2025-03-15',
            'room': 'Stora Salen',
            'ticket_info': 'Tickets available at venue',
            'email_date': '2025-01-15 12:00:00',
            'source_sender': 'info@nalen.se',
            'source_subject': 'Upcoming Concert: Test Band at Nalen',
            'email_id': 'dummy_concert_001',
            'processed_date': '2025-01-15 15:45:00'
        }]
    
    # Export dummy results
    extractor_output_files = email_processor.get_extractor_output_files()
    for extractor_name, items in dummy_results.items():
        if extractor_name in extractor_output_files:
            output_file = extractor_output_files[extractor_name]
            csv_exporter.export_extractor_data(extractor_name, items, output_file)
    
    logger.info("✓ Dummy data test completed successfully")
    return 0

if __name__ == "__main__":
    exit(main())