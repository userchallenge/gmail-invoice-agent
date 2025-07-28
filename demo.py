import argparse
import yaml
import os
import logging
from typing import Optional
from dotenv import load_dotenv
from agents.email_processor import EmailProcessor
from gmail_server import GmailServer
from csv_exporter import CSVExporter

logger = logging.getLogger(__name__)

def setup_logging(log_file: Optional[str] = None):
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
    parser.add_argument('--extractors', nargs='+', 
                       choices=['invoices', 'concerts', 'all'], 
                       help='Specific extractors to run: invoices, concerts, or all', 
                       default=['all'])
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
    if 'all' not in args.extractors:
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
    else:
        logger.info("Running all enabled extractors")
    
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
    
    # Show extractor-specific messages
    extractor_icons = {'invoices': '🧾', 'concerts': '🎵'}
    for extractor in enabled_extractors:
        icon = extractor_icons.get(extractor, '📄')
        if extractor == 'invoices':
            logger.info(f"{icon} Invoice extraction enabled")
        elif extractor == 'concerts':
            logger.info(f"{icon} Concert extraction enabled (all of Sweden)")
        else:
            logger.info(f"{icon} {extractor.title()} extraction enabled")
    
    logger.info(f"Active extractors: {', '.join(enabled_extractors)}")
    
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
    """Run extraction from Gmail - each extractor runs its own search"""
    days_back = config['processing']['default_days_back']
    
    # Get enabled extractors and run separate searches for each
    enabled_extractors = email_processor.get_enabled_extractors()
    all_emails = {}  # emails per extractor
    all_results = {}
    
    for extractor_name in enabled_extractors:
        # Get extractor-specific search criteria
        extractor = email_processor.get_extractor_by_name(extractor_name)
        if not extractor:
            continue
            
        search_keywords = extractor.get_search_keywords()
        search_filters = extractor.get_additional_search_filters()
        
        logger.info(f"🔍 Searching for {extractor_name} emails with {len(search_keywords)} keywords and {len(search_filters)} filters")
        logger.debug(f"{extractor_name} keywords: {search_keywords[:5]}...")  # Show first 5
        
        # Fetch emails for this specific extractor
        emails = gmail_server.fetch_emails_for_extractors(search_keywords, search_filters, days_back)
        all_emails[extractor_name] = emails
        logger.info(f"📧 Found {len(emails)} {extractor_name} emails")
    
    # Process emails for each extractor separately  
    for extractor_name, emails in all_emails.items():
        if not emails:
            logger.info(f"No {extractor_name} emails to process")
            continue
            
        logger.info(f"🔄 Processing {len(emails)} {extractor_name} emails...")
        extractor_results = []
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
                
                # Process with specific extractor only
                extractor = email_processor.get_extractor_by_name(extractor_name)
                if extractor:
                    results = extractor.extract(email_content, email_metadata)
                    extractor_results.extend(results)
                
                processed_count += 1
                if processed_count % 10 == 0:
                    logger.info(f"Processed {processed_count}/{len(emails)} {extractor_name} emails...")
                    
            except Exception as e:
                logger.error(f"Error processing {extractor_name} email {email['id']}: {e}")
                continue
        
        # Store results for this extractor
        if extractor_results:
            all_results[extractor_name] = extractor_results
            logger.info(f"✅ {extractor_name}: {len(extractor_results)} items extracted")
    
    # Export results for each extractor
    extractor_output_files = email_processor.get_extractor_output_files()
    for extractor_name, items in all_results.items():
        if extractor_name in extractor_output_files:
            output_file = extractor_output_files[extractor_name]
            csv_exporter.export_extractor_data(extractor_name, items, output_file)
    
    # Summary statistics
    logger.info("\n=== EXTRACTION SUMMARY ===")
    total_items = 0
    total_emails_processed = sum(len(emails) for emails in all_emails.values())
    
    for extractor_name, items in all_results.items():
        count = len(items)
        total_items += count
        logger.info(f"📊 {extractor_name.title()}: {count} items extracted")
    
    logger.info(f"📈 Total: {total_items} items from {total_emails_processed} emails")
    
    # Show sample results for each extractor
    for extractor_name, items in all_results.items():
        if items:
            logger.info(f"\n📄 Sample {extractor_name} data:")
            sample_item = items[0]
            for key, value in list(sample_item.items())[:5]:  # Show first 5 fields
                logger.info(f"   {key}: {str(value)[:50]}...")
    
    return 0

def run_dummy_data_test(email_processor, csv_exporter, config):
    """Run extraction with dummy data for testing - use pytest for comprehensive testing"""
    logger.info("Dummy data testing - for full testing use: pytest tests/")
    logger.info("Creating minimal sample data for enabled extractors")
    
    enabled_extractors = email_processor.get_enabled_extractors()
    dummy_results = {}
    
    # Create minimal dummy data for quick validation
    if 'invoices' in enabled_extractors:
        dummy_results['invoices'] = [{
            'email_id': 'demo_invoice_001',
            'email_subject': 'Demo Invoice',
            'email_sender': 'demo@example.com',
            'email_date': '2025-01-15 10:30:00',
            'vendor': 'Demo Company',
            'invoice_number': 'DEMO-001',
            'amount': '100.00',
            'currency': 'SEK',
            'due_date': '2025-02-15',
            'invoice_date': '2025-01-15',
            'ocr': '',
            'description': 'Demo invoice',
            'confidence': 1.0,
            'processed_date': '2025-01-15 15:45:00',
            'pdf_processed': False,
            'pdf_filename': '',
            'pdf_text_length': 0,
            'pdf_processing_error': ''
        }]
    
    if 'concerts' in enabled_extractors:
        dummy_results['concerts'] = [{
            'artist': 'Demo Band',
            'venue': 'Demo Venue',
            'town': 'Stockholm',
            'date': '2025-03-15',
            'room': 'Main Stage',
            'ticket_info': 'Demo tickets',
            'email_date': '2025-01-15 12:00:00',
            'source_sender': 'demo@venue.se',
            'source_subject': 'Demo Concert',
            'email_id': 'demo_concert_001',
            'processed_date': '2025-01-15 15:45:00'
        }]
    
    # Export dummy results
    extractor_output_files = email_processor.get_extractor_output_files()
    for extractor_name, items in dummy_results.items():
        if extractor_name in extractor_output_files:
            output_file = extractor_output_files[extractor_name]
            csv_exporter.export_extractor_data(extractor_name, items, output_file)
    
    logger.info("✓ Demo data generated - run 'pytest tests/' for comprehensive testing")
    return 0

if __name__ == "__main__":
    exit(main())