#!/usr/bin/env python3
"""
Gmail Invoice Agent - Demo Script
Extracts invoice data from Gmail and exports to CSV
"""

import argparse
import yaml
import logging
import os
import sys
from datetime import datetime
from tqdm import tqdm

# Import our modules
from gmail_server import GmailServer
from email_classifier import EmailClassifier
from csv_exporter import CSVExporter

from typing import Optional


def setup_logging(log_file: Optional[str] = None):
    """Setup logging configuration"""
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        logging.basicConfig(
            level=logging.INFO,
            format=log_format,
            handlers=[logging.FileHandler(log_file), logging.StreamHandler(sys.stdout)],
        )
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)


def load_config(config_path: str) -> dict:
    """Load configuration from YAML file"""
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # Validate required keys
        required_keys = ["claude", "gmail", "processing", "output"]
        for key in required_keys:
            if key not in config:
                raise ValueError(f"Missing required config section: {key}")

        return config
    except Exception as e:
        print(f"❌ Error loading config from {config_path}: {e}")
        sys.exit(1)


def validate_credentials(config: dict):
    """Validate that required credentials are available"""
    # Check Claude API key
    claude_key = config["claude"]["api_key"]
    if not claude_key or claude_key == "your-claude-api-key-here":
        print("❌ Please set your Claude API key in config/config.yaml")
        sys.exit(1)

    # Check Gmail credentials file
    gmail_creds = config["gmail"]["credentials_file"]
    if not os.path.exists(gmail_creds):
        print(f"❌ Gmail credentials file not found: {gmail_creds}")
        print(
            "Please download credentials.json from Google Cloud Console and place it at this location"
        )
        sys.exit(1)


def print_banner():
    """Print application banner"""
    print("=" * 60)
    print("📧 Gmail Invoice Agent - AI-Powered Invoice Extraction")
    print("=" * 60)
    print()


def process_emails(
    gmail_server: GmailServer, classifier: EmailClassifier, config: dict
) -> list:
    """Process emails and extract invoice data"""
    print("🔍 Fetching emails from Gmail...")

    emails = gmail_server.fetch_emails(
        days_back=config["processing"]["default_days_back"],
        max_emails=config["processing"]["max_emails"],
    )

    if not emails:
        print("❌ No emails found or error fetching emails")
        return []

    print(f"📧 Found {len(emails)} potential invoice emails")
    print("\n🤖 Processing emails with Claude AI...")

    invoice_data = []

    # Process emails with progress bar
    for email in tqdm(emails, desc="Processing emails"):
        try:
            extracted_data = classifier.classify_and_extract(email)
            if extracted_data:
                invoice_data.append(extracted_data)
        except Exception as e:
            logging.error(
                f"Error processing email {email.get('subject', 'Unknown')}: {e}"
            )
            continue

    return invoice_data


def print_results(invoice_data: list, stats: dict):
    """Print processing results"""
    print(f"\n✅ Processing Complete!")
    print(f"📊 Results Summary:")
    print(f"   • Total invoices found: {len(invoice_data)}")

    if stats:
        print(f"   • Total amount: {stats.get('total_amount', 0):.2f} SEK")
        print(f"   • Average amount: {stats.get('avg_amount', 0):.2f} SEK")

        if "top_vendors" in stats:
            print(
                f"   • Top vendors: {', '.join(list(stats['top_vendors'].keys())[:3])}"
            )

    print()


def main():
    """Main application entry point"""
    parser = argparse.ArgumentParser(
        description="Extract invoice data from Gmail using AI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python demo.py                           # Use default config
  python demo.py --config my_config.yaml  # Use custom config
  python demo.py --days-back 7            # Process last 7 days only
        """,
    )

    parser.add_argument(
        "--config",
        default="config/config.yaml",
        help="Configuration file path (default: config/config.yaml)",
    )

    parser.add_argument(
        "--days-back", type=int, help="Number of days back to search (overrides config)"
    )

    parser.add_argument(
        "--max-emails",
        type=int,
        help="Maximum number of emails to process (overrides config)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Print banner
    print_banner()

    # Load configuration
    print(f"📄 Loading configuration from {args.config}...")
    config = load_config(args.config)

    # Override config with command line args
    if args.days_back:
        config["processing"]["default_days_back"] = args.days_back
    if args.max_emails:
        config["processing"]["max_emails"] = args.max_emails

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.getLogger().setLevel(log_level)

    if "log_file" in config["output"]:
        setup_logging(config["output"]["log_file"])
    else:
        setup_logging()

    # Validate credentials
    validate_credentials(config)

    try:
        # Initialize components
        print("🔐 Authenticating with Gmail...")
        gmail_server = GmailServer(
            credentials_file=config["gmail"]["credentials_file"],
            token_file=config["gmail"]["token_file"],
            scopes=config["gmail"]["scopes"],
        )

        print("🧠 Initializing Claude AI classifier...")
        classifier = EmailClassifier(api_key=config["claude"]["api_key"], config=config)

        print("📁 Setting up CSV exporter...")
        exporter = CSVExporter(config["output"]["invoices_file"])

        # Process emails
        invoice_data = process_emails(gmail_server, classifier, config)

        if invoice_data:
            # Export to CSV
            print(f"💾 Exporting {len(invoice_data)} invoices to CSV...")
            success = exporter.append_invoices(invoice_data)

            if success:
                # Get and display stats
                stats = exporter.get_summary_stats()
                print_results(invoice_data, stats)

                print(
                    f"📄 Invoice data exported to: {config['output']['invoices_file']}"
                )

                # Show sample data
                if len(invoice_data) > 0:
                    print("\n📋 Sample extracted invoice:")
                    sample = invoice_data[0]
                    print(f"   • Vendor: {sample.get('vendor', 'N/A')}")
                    print(
                        f"   • Amount: {sample.get('amount', 'N/A')} {sample.get('currency', 'SEK')}"
                    )
                    print(f"   • Due Date: {sample.get('due_date', 'N/A')}")
                    print(f"   • Invoice #: {sample.get('invoice_number', 'N/A')}")
                    if sample.get("ocr"):
                        print(f"   • OCR: {sample.get('ocr')}")
            else:
                print("❌ Failed to export invoice data")
                sys.exit(1)
        else:
            print("📭 No invoices found in the processed emails")
            print("This could mean:")
            print("   • No invoice emails in the date range")
            print("   • Invoices not recognized by AI classifier")
            print("   • All found invoices were already processed")

    except KeyboardInterrupt:
        print("\n\n⏹️  Processing interrupted by user")
        sys.exit(0)
    except Exception as e:
        logging.error(f"Application error: {e}")
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
