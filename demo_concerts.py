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
            handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
        )
    else:
        logging.basicConfig(level=logging.INFO, format=log_format)


def main():
    # Load environment variables
    load_dotenv()

    parser = argparse.ArgumentParser(description="Gmail Concert Extractor")
    parser.add_argument(
        "--config", default="config/config.yaml", help="Config file path"
    )
    parser.add_argument(
        "--dummy-data", action="store_true", help="Use test data instead of Gmail API"
    )
    parser.add_argument(
        "--days-back", type=int, help="Number of days back to search", default=None
    )
    args = parser.parse_args()

    # Load configuration
    try:
        with open(args.config, "r") as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        logger.error(f"Config file not found: {args.config}")
        return 1
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return 1

    # Force enable only concerts
    extractors_config = config.get("extractors", {})
    for name in extractors_config:
        extractors_config[name]["enabled"] = name == "concerts"

    # Override days back if specified
    if args.days_back:
        config["processing"]["default_days_back"] = args.days_back
        logger.info(f"Using custom days back: {args.days_back}")

    # Setup logging
    if "log_file" in config["output"]:
        setup_logging(config["output"]["log_file"])
    else:
        setup_logging()

    # Get Claude API key from environment
    claude_api_key = os.getenv("CLAUDE_API_KEY")
    if not claude_api_key:
        logger.error("CLAUDE_API_KEY not found in environment variables")
        logger.error("Please create a .env file with: CLAUDE_API_KEY=your_api_key_here")
        return 1

    # Initialize components
    try:
        email_processor = EmailProcessor(config, claude_api_key)
        gmail_server = GmailServer(
            config["gmail"]["credentials_file"],
            config["gmail"]["token_file"],
            config["gmail"]["scopes"],
            config,
        )
        csv_exporter = CSVExporter()
    except Exception as e:
        logger.error(f"Error initializing components: {e}")
        return 1

    logger.info("=== Gmail Concert Extractor ===")
    logger.info("🎵 Extracting concert data for all of Sweden")

    try:
        if args.dummy_data:
            logger.info("Using dummy concert data for testing...")
            return run_dummy_concert_test(email_processor, csv_exporter, config)
        else:
            return run_concert_extraction(
                email_processor, gmail_server, csv_exporter, config
            )

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback

        traceback.print_exc()
        return 1


def run_concert_extraction(email_processor, gmail_server, csv_exporter, config):
    """Run concert extraction from Gmail"""
    # Get concert keywords and filters only
    search_keywords = email_processor.get_search_keywords()
    search_filters = email_processor.get_search_filters()
    logger.info(f"Searching for concert emails with {len(search_keywords)} keywords and {len(search_filters)} filters...")

    # Fetch emails
    days_back = config["processing"]["default_days_back"]
    emails = gmail_server.fetch_emails_for_extractors(search_keywords, search_filters, days_back)
    logger.info(f"Found {len(emails)} potential concert emails")

    if not emails:
        logger.info("No emails found matching concert criteria")
        return 0

    # Process emails
    concert_results = []
    processed = 0

    for email in emails:
        try:
            email_content = gmail_server.get_email_content(email["id"])
            email_metadata = {
                "date": email.get("date", ""),
                "sender": email.get("sender", ""),
                "subject": email.get("subject", ""),
                "id": email["id"],
                "attachments": email.get("attachments", []),
                "pdf_processed": email.get("pdf_processed", False),
                "pdf_filename": email.get("pdf_filename", ""),
                "pdf_text": email.get("pdf_text", ""),
                "pdf_text_length": email.get("pdf_text_length", 0),
                "pdf_processing_error": email.get("pdf_processing_error", ""),
            }

            results = email_processor.process_email(email_content, email_metadata)

            if "concerts" in results:
                concert_results.extend(results["concerts"])
                num_concerts = len(results["concerts"])
                logger.info(
                    f"🎤 Found {num_concerts} concert(s) in: {email_metadata['subject'][:50]}..."
                )

            processed += 1
            if processed % 10 == 0:
                logger.info(f"Processed {processed}/{len(emails)} emails...")

        except Exception as e:
            logger.error(f"Error processing email: {e}")
            continue

    # Export results
    if concert_results:
        output_file = config["extractors"]["concerts"]["output_file"]
        csv_exporter.export_extractor_data("concerts", concert_results, output_file)

        # Show concert details
        logger.info("\n🎵 CONCERTS FOUND:")
        for i, concert in enumerate(concert_results[:10]):  # Show first 10
            artist = concert.get("artist", "Unknown Artist")
            venue = concert.get("venue", "Unknown Venue")
            town = concert.get("town", "Unknown Town")
            date = concert.get("date", "Unknown Date")
            room = concert.get("room", "")
            room_info = f" ({room})" if room else ""
            logger.info(f"   {i+1}. {artist} at {venue}, {town}{room_info} on {date}")

        if len(concert_results) > 10:
            logger.info(f"   ... and {len(concert_results) - 10} more")

    logger.info(
        f"\n📊 CONCERT SUMMARY: {len(concert_results)} concerts from {processed} emails"
    )

    if concert_results:
        # Group by venue
        venue_counts = {}
        for concert in concert_results:
            venue = concert.get("venue", "Unknown")
            venue_counts[venue] = venue_counts.get(venue, 0) + 1

        if venue_counts:
            logger.info("🎪 Concerts by venue:")
            for venue, count in sorted(
                venue_counts.items(), key=lambda x: x[1], reverse=True
            ):
                logger.info(f"   {venue}: {count} concert(s)")

    return 0


def run_dummy_concert_test(email_processor, csv_exporter, config):
    """Run extraction with dummy concert data for testing"""
    logger.info("Creating dummy concert data for testing...")

    dummy_concerts = [
        {
            "artist": "Arctic Monkeys",
            "venue": "Annexet",
            "town": "Stockholm",
            "date": "2025-03-15",
            "room": "Main Hall",
            "ticket_info": "Tickets on sale Friday 10:00",
            "email_date": "2025-01-15 12:00:00",
            "source_sender": "info@annexet.se",
            "source_subject": "Arctic Monkeys - Live at Annexet March 15",
            "email_id": "dummy_concert_001",
            "processed_date": "2025-01-15 15:45:00",
        },
        {
            "artist": "Dua Lipa",
            "venue": "Ullevi",
            "town": "Göteborg",
            "date": "2025-04-22",
            "room": "",
            "ticket_info": "VIP packages available",
            "email_date": "2025-01-12 14:30:00",
            "source_sender": "tickets@ullevi.se",
            "source_subject": "Dua Lipa kommer till Ullevi!",
            "email_id": "dummy_concert_002",
            "processed_date": "2025-01-15 15:45:00",
        },
        {
            "artist": "Veronica Maggio",
            "venue": "Malmö Arena",
            "town": "Malmö",
            "date": "2025-05-10",
            "room": "",
            "ticket_info": "Members get early access",
            "email_date": "2025-01-14 09:45:00",
            "source_sender": "events@malmoarena.se",
            "source_subject": "Veronica Maggio kommer till Malmö Arena",
            "email_id": "dummy_concert_003",
            "processed_date": "2025-01-15 15:45:00",
        },
    ]

    # Export dummy results
    output_file = config["extractors"]["concerts"]["output_file"]
    csv_exporter.export_extractor_data("concerts", dummy_concerts, output_file)

    logger.info(f"✓ Created {len(dummy_concerts)} dummy concerts")
    logger.info("🎵 Dummy concerts:")
    for i, concert in enumerate(dummy_concerts, 1):
        artist = concert["artist"]
        venue = concert["venue"]
        town = concert["town"]
        date = concert["date"]
        logger.info(f"   {i}. {artist} at {venue}, {town} on {date}")

    logger.info("✓ Dummy concert test completed successfully")
    return 0


if __name__ == "__main__":
    exit(main())
