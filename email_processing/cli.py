#!/usr/bin/env python3

import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import time
import yaml
from datetime import datetime
from dotenv import load_dotenv
from gmail_server import GmailServer
from email_processing.database.db_manager import EmailDatabaseManager
from email_processing.agents.categorization_agent import EmailCategorizationAgent
from email_processing.agents.summary_agent import EmailSummaryAgent
from email_processing.agents.task_agent import EmailTaskAgent


def load_config():
    """Load configuration from existing config file."""
    config_path = "config/config.yaml"
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    return {}


def validate_date_args(args):
    """Validate and resolve date argument conflicts."""
    date_options = []
    if args.date:
        date_options.append("--date")
    if args.from_date:
        date_options.append("--from-date")
    if args.to_date:
        date_options.append("--to-date")
    if args.days != 1:  # Only count if explicitly set (not default)
        date_options.append("--days")
    
    # Check for conflicting options
    if args.date and (args.from_date or args.to_date):
        print("Error: --date cannot be used with --from-date or --to-date")
        return False
    
    if args.to_date and not args.from_date:
        print("Error: --to-date requires --from-date")
        return False
    
    # Validate date formats
    date_format = "%Y-%m-%d"
    try:
        if args.date:
            datetime.strptime(args.date, date_format)
        if args.from_date:
            datetime.strptime(args.from_date, date_format)
        if args.to_date:
            datetime.strptime(args.to_date, date_format)
            # Validate date range
            from_dt = datetime.strptime(args.from_date, date_format)
            to_dt = datetime.strptime(args.to_date, date_format)
            if to_dt < from_dt:
                print("Error: --to-date must be after --from-date")
                return False
    except ValueError as e:
        print(f"Error: Invalid date format. Use YYYY-MM-DD format. {e}")
        return False
    
    return True


def fetch_and_store_emails(days_back: int = None, from_date: str = None, to_date: str = None, single_date: str = None):
    """Fetch emails and store them in the database with flexible date options."""
    
    # Determine date parameters and description
    if single_date:
        print(f"Fetching emails from single date: {single_date}")
        start_date, end_date = single_date, single_date
    elif from_date and to_date:
        print(f"Fetching emails from date range: {from_date} to {to_date}")
        start_date, end_date = from_date, to_date
    elif from_date:
        print(f"Fetching emails from {from_date} to now")
        start_date, end_date = from_date, None
    else:
        days = days_back if days_back is not None else 1
        print(f"Fetching emails from the last {days} days")
        start_date, end_date = None, None
    
    config = load_config()
    
    # Initialize Gmail server
    gmail_server = GmailServer(
        credentials_file="config/gmail_credentials.json",
        token_file="config/gmail_token.json",
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        config=config
    )
    
    # Fetch ALL emails using new universal method
    emails = gmail_server.fetch_all_emails(
        days_back=days_back,
        start_date=start_date,
        end_date=end_date
    )
    
    print(f"Found {len(emails)} emails")
    
    # Initialize database and store emails
    db_manager = EmailDatabaseManager()
    db_manager.initialize_database()
    
    for email in emails:
        db_manager.store_email(email)
    
    print(f"Stored {len(emails)} emails in database")
    return len(emails)


def smart_truncate_content(content: str, max_length: int = 1500) -> str:
    """Smart content truncation preserving beginning and end context."""
    if len(content) <= max_length:
        return content
    
    # Keep first 1000 chars and last 500 chars for context
    first_part = content[:1000]
    last_part = content[-(max_length-1000-20):]  # -20 for separator
    
    return f"{first_part}\n...[truncated]...\n{last_part}"


def should_include_pdf(body_length: int, pdf_length: int) -> bool:
    """Decide whether to include PDF content based on body length."""
    # Skip PDF if body has sufficient content (>500 chars)
    if body_length > 500:
        return False
    # Include PDF if body is minimal but PDF has content
    return pdf_length > 0


def retry_with_backoff(func, *args, max_retries=3, **kwargs):
    """Retry function with exponential backoff for rate limit errors."""
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "rate_limit_error" in error_str.lower():
                if attempt < max_retries - 1:  # Don't sleep on last attempt
                    # Parse retry-after from error message if available
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    print(f"  Rate limit hit, waiting {wait_time}s before retry {attempt + 2}/{max_retries}")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  Rate limit: Max retries exceeded")
                    raise
            else:
                # Non-rate limit error, don't retry
                raise
    
    # Should never reach here
    raise Exception("Retry logic error")


def categorize_emails():
    """Categorize uncategorized emails with token reduction and rate limiting."""
    print("Categorizing emails...")
    
    db_manager = EmailDatabaseManager()
    categorization_agent = EmailCategorizationAgent()
    
    uncategorized_emails = db_manager.get_uncategorized_emails()
    print(f"Found {len(uncategorized_emails)} uncategorized emails")
    
    successful_count = 0
    failed_count = 0
    
    for i, email in enumerate(uncategorized_emails, 1):
        print(f"Processing email {i}/{len(uncategorized_emails)}: {email.subject[:50]}...")
        
        # Apply token reduction strategies
        original_body = email.body_clean or ""
        original_pdf = email.pdf_text or ""
        
        # Smart truncation of body content
        truncated_body = smart_truncate_content(original_body)
        
        # Smart PDF inclusion (skip if body has enough context)
        include_pdf = should_include_pdf(len(original_body), len(original_pdf))
        pdf_content = smart_truncate_content(original_pdf, 1000) if include_pdf else ""
        
        email_data = {
            "email_id": email.email_id,
            "sender": email.sender,
            "subject": email.subject,
            "body_clean": truncated_body,
            "pdf_text": pdf_content
        }
        
        try:
            # Use retry with exponential backoff for rate limit errors
            result = retry_with_backoff(categorization_agent.categorize_email, email_data)
            
            db_manager.store_categorization(
                email_id=email.email_id,
                category_name=result["category"],
                agent_name="EmailCategorizationAgent",
                model_version="claude-3-5-sonnet-20241022",
                ai_reasoning=result["ai_reasoning"]
            )
            
            print(f"✓ Categorized as: {result['category']}")
            successful_count += 1
            
        except Exception as e:
            print(f"✗ Error categorizing email: {e}")
            print(f"  Subject: {email.subject}")
            print(f"  Sender: {email.sender}")
            failed_count += 1
            continue
        
        # Rate limiting: Increased delay to prevent acceleration limits
        if i < len(uncategorized_emails):  # Don't delay after the last email
            time.sleep(2.0)  # 2 second delay for gradual ramping
    
    print(f"\nCategorization complete:")
    print(f"  ✓ Successful: {successful_count} emails")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} emails")
    
    return successful_count


def summarize_information_emails():
    """Summarize information emails with token reduction and rate limiting."""
    print("Summarizing information emails...")
    
    db_manager = EmailDatabaseManager()
    summary_agent = EmailSummaryAgent()
    
    emails_to_summarize = db_manager.get_information_emails_without_summary()
    print(f"Found {len(emails_to_summarize)} information emails to summarize")
    
    successful_count = 0
    failed_count = 0
    
    for i, email in enumerate(emails_to_summarize, 1):
        print(f"Processing email {i}/{len(emails_to_summarize)}: {email.subject[:50]}...")
        
        # Apply token reduction strategies (same as categorization)
        original_body = email.body_clean or ""
        original_pdf = email.pdf_text or ""
        
        # Smart truncation of body content
        truncated_body = smart_truncate_content(original_body)
        
        # Smart PDF inclusion (skip if body has enough context)
        include_pdf = should_include_pdf(len(original_body), len(original_pdf))
        pdf_content = smart_truncate_content(original_pdf, 1000) if include_pdf else ""
        
        email_data = {
            "email_id": email.email_id,
            "sender": email.sender,
            "subject": email.subject,
            "body_clean": truncated_body,
            "pdf_text": pdf_content
        }
        
        try:
            # Use retry with exponential backoff for rate limit errors
            result = retry_with_backoff(summary_agent.summarize_email, email_data)
            
            db_manager.store_summary(
                email_id=email.email_id,
                email_summary=result["email_summary"],
                ai_reasoning=result["ai_reasoning"],
                agent_name="EmailSummaryAgent",
                model_version="claude-3-5-sonnet-20241022"
            )
            
            print(f"✓ Summarized successfully")
            successful_count += 1
            
        except Exception as e:
            print(f"✗ Error summarizing email: {e}")
            print(f"  Subject: {email.subject}")
            print(f"  Sender: {email.sender}")
            failed_count += 1
            continue
        
        # Rate limiting: Same delay as categorization
        if i < len(emails_to_summarize):  # Don't delay after the last email
            time.sleep(2.0)  # 2 second delay for gradual ramping
    
    print(f"\nSummarization complete:")
    print(f"  ✓ Successful: {successful_count} emails")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} emails")
    
    return successful_count


def process_action_tasks():
    """Process action emails to extract tasks with token reduction and rate limiting."""
    print("Processing action emails for task extraction...")
    
    db_manager = EmailDatabaseManager()
    task_agent = EmailTaskAgent()
    
    emails_to_process = db_manager.get_action_emails_without_tasks()
    print(f"Found {len(emails_to_process)} action emails to process for tasks")
    
    successful_count = 0
    failed_count = 0
    
    for i, email in enumerate(emails_to_process, 1):
        print(f"Processing email {i}/{len(emails_to_process)}: {email.subject[:50]}...")
        
        # Apply token reduction strategies (same as categorization)
        original_body = email.body_clean or ""
        original_pdf = email.pdf_text or ""
        
        # Smart truncation of body content
        truncated_body = smart_truncate_content(original_body)
        
        # Smart PDF inclusion (skip if body has enough context)
        include_pdf = should_include_pdf(len(original_body), len(original_pdf))
        pdf_content = smart_truncate_content(original_pdf, 1000) if include_pdf else ""
        
        email_data = {
            "email_id": email.email_id,
            "sender": email.sender,
            "subject": email.subject,
            "body_clean": truncated_body,
            "pdf_text": pdf_content,
        }
        
        try:
            # Use retry with exponential backoff for rate limit errors
            result = retry_with_backoff(task_agent.analyze_task, email_data)
            
            db_manager.store_task(
                email_id=email.email_id,
                action_required=result["action_required"],
                assigned_to=result["assigned_to"], 
                due_date=result["due_date"],
                priority=result["priority"],
                ai_reasoning=result["ai_reasoning"],
                agent_name="EmailTaskAgent",
                model_version="claude-3-5-sonnet-20241022"
            )
            
            print(f"✓ Task extracted successfully")
            successful_count += 1
            
        except Exception as e:
            print(f"✗ Error processing task: {str(e)}")
            failed_count += 1
            continue
        
        # Rate limiting: Same delay as categorization
        if i < len(emails_to_process):  # Don't delay after the last email
            time.sleep(2.0)  # 2 second delay for gradual ramping
    
    print(f"\nTask processing complete:")
    print(f"  ✓ Successful: {successful_count} emails")
    if failed_count > 0:
        print(f"  ✗ Failed: {failed_count} emails")
    
    return successful_count


def show_stats():
    """Show processing statistics."""
    db_manager = EmailDatabaseManager()
    db_manager.initialize_database()
    stats = db_manager.get_processing_stats()
    
    print("\nProcessing Statistics:")
    print(f"Total emails: {stats['total_emails']}")
    print(f"Categorized emails: {stats['categorized_emails']}")
    print(f"Summarized emails: {stats['summarized_emails']}")


def delete_all_tables(force: bool = False):
    """Empty all database tables."""
    db_manager = EmailDatabaseManager()
    db_manager.initialize_database()
    
    # Show current stats before deletion
    counts = db_manager.get_table_counts()
    print("\nCurrent database contents:")
    for table, count in counts.items():
        print(f"  {table}: {count} records")
    
    # Confirm deletion unless forced
    if not force:
        response = input("\nAre you sure you want to empty ALL database tables? (yes/no): ")
        if response.lower() != "yes":
            print("Operation cancelled.")
            return
    
    print("Emptying all database tables...")
    db_manager.delete_all_tables()
    print("✓ All database tables emptied successfully")
    print("✓ Categories re-populated with initial data")


def delete_processing_results(force: bool = False):
    """Clear categorizations and summaries tables."""
    db_manager = EmailDatabaseManager()
    db_manager.initialize_database()
    
    # Show current stats before deletion
    stats = db_manager.get_processing_stats()
    print(f"\nCurrent processing results:")
    print(f"  Categorizations: {stats['categorized_emails']} emails")
    print(f"  Summaries: {stats['summarized_emails']} summaries")
    
    # Confirm deletion unless forced
    if not force:
        response = input("\nAre you sure you want to clear all processing results? (yes/no): ")
        if response.lower() != "yes":
            print("Operation cancelled.")
            return
    
    print("Clearing processing results...")
    db_manager.delete_result_tables()
    print("✓ Categorizations and summaries cleared successfully")
    print("✓ Email categories reset to uncategorized")


def delete_specific_table(table_name: str, force: bool = False):
    """Clear specific result table."""
    db_manager = EmailDatabaseManager()
    db_manager.initialize_database()
    
    # Show current count before deletion
    counts = db_manager.get_table_counts()
    print(f"\nCurrent {table_name} table: {counts[table_name]} records")
    
    # Confirm deletion unless forced
    if not force:
        response = input(f"\nAre you sure you want to clear the {table_name} table? (yes/no): ")
        if response.lower() != "yes":
            print("Operation cancelled.")
            return
    
    print(f"Clearing {table_name} table...")
    db_manager.delete_result_table(table_name)
    print(f"✓ {table_name.capitalize()} table cleared successfully")
    
    if table_name == "categorizations":
        print("✓ Email categories reset to uncategorized")


def run_full_pipeline(days_back: int = None, from_date: str = None, to_date: str = None, single_date: str = None):
    """Run the complete email processing pipeline."""
    print("Starting email processing pipeline...")
    
    # Step 1: Fetch and store emails
    email_count = fetch_and_store_emails(days_back, from_date, to_date, single_date)
    
    # Step 2: Categorize emails
    categorized_count = categorize_emails()
    
    # Step 3: Summarize information emails
    summarized_count = summarize_information_emails()
    
    # Step 4: Process action emails for tasks
    task_count = process_action_tasks()
    
    # Step 5: Show final statistics
    show_stats()
    
    print(f"\nPipeline complete!")
    print(f"Processed {email_count} emails, categorized {categorized_count}, summarized {summarized_count}, extracted {task_count} tasks")


def main():
    # Load environment variables from .env file
    load_dotenv()
    
    parser = argparse.ArgumentParser(description="Email Processing Pipeline")
    parser.add_argument(
        "--days", 
        type=int, 
        default=1, 
        help="Number of days back to fetch emails (default: 1)"
    )
    parser.add_argument(
        "--from-date", 
        type=str, 
        help="Fetch emails from specific date to now (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--to-date", 
        type=str, 
        help="End date for date range (YYYY-MM-DD format, use with --from-date)"
    )
    parser.add_argument(
        "--date", 
        type=str, 
        help="Fetch emails from single specific date (YYYY-MM-DD format)"
    )
    parser.add_argument(
        "--fetch-only", 
        action="store_true", 
        help="Only fetch and store emails"
    )
    parser.add_argument(
        "--categorize-only", 
        action="store_true", 
        help="Only categorize existing emails"
    )
    parser.add_argument(
        "--summarize-only", 
        action="store_true", 
        help="Only summarize existing information emails"
    )
    parser.add_argument(
        "--tasks-only", 
        action="store_true", 
        help="Only process existing action emails for task extraction"
    )
    parser.add_argument(
        "--stats", 
        action="store_true", 
        help="Show processing statistics"
    )
    parser.add_argument(
        "--delete-database", 
        action="store_true", 
        help="Empty all database tables (keeps database file structure)"
    )
    parser.add_argument(
        "--delete-result-tables", 
        action="store_true", 
        help="Clear categorizations, summaries, and tasks tables (keep emails)"
    )
    parser.add_argument(
        "--delete-result-table", 
        action="store_true", 
        help="Clear specific result table (use with --table)"
    )
    parser.add_argument(
        "--table", 
        choices=["categorizations", "summaries", "tasks"],
        help="Specify table to delete (categorizations, summaries, or tasks)"
    )
    parser.add_argument(
        "--force", 
        action="store_true", 
        help="Skip confirmation prompts for delete operations"
    )
    
    args = parser.parse_args()
    
    # Validate date arguments
    if not validate_date_args(args):
        return
    
    # Handle database management commands
    if args.delete_database:
        delete_all_tables(force=args.force)
    elif args.delete_result_tables:
        delete_processing_results(force=args.force)
    elif args.delete_result_table:
        if not args.table:
            print("Error: --delete-result-table requires --table parameter")
            print("Usage: --delete-result-table --table categorizations")
            print("       --delete-result-table --table summaries")
            print("       --delete-result-table --table tasks")
            return
        delete_specific_table(args.table, force=args.force)
    # Handle processing commands
    elif args.fetch_only:
        fetch_and_store_emails(args.days, args.from_date, args.to_date, args.date)
    elif args.categorize_only:
        categorize_emails()
    elif args.summarize_only:
        summarize_information_emails()
    elif args.tasks_only:
        process_action_tasks()
    elif args.stats:
        show_stats()
    else:
        run_full_pipeline(args.days, args.from_date, args.to_date, args.date)


if __name__ == "__main__":
    main()