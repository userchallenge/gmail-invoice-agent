"""
Zero Inbox Runner
Clean Python implementation converting the notebook functionality into a class-based approach.
Provides minimal code execution with flexible method ordering.
"""

import yaml
import logging
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any, Union

from models.zero_inbox_models import DatabaseManager, Email, EmailCategory
from zero_inbox_fetcher import ZeroInboxEmailFetcher
from email_categorization_agent import EmailCategorizationAgent
from llm_client_factory import validate_all_providers


class ZeroInboxAgent:
    """
    Clean Zero Inbox Agent with minimal output and flexible execution.

    Usage:
        agent = ZeroInboxAgent()
        agent.run()  # Full pipeline
        agent.run(['setup', 'fetch_emails'])  # Specific methods
        agent.run(['categorize_emails'], categorize_emails={'batch_size': 10})
    """

    def __init__(
        self,
        config_path: str = "config/config.yaml",
        db_path: str = "sqlite:///data/zero_inbox.db",
    ):
        self.config_path = config_path
        self.db_path = db_path
        self.config = None
        self.db_manager = None
        self.email_fetcher = None
        self.categorization_agent = None

    def setup(self) -> Dict[str, Any]:
        """Initialize database, Gmail connection, and categorization agent."""
        # Load configuration
        with open(self.config_path, "r") as f:
            self.config = yaml.safe_load(f)

        # Initialize database
        self.db_manager = DatabaseManager(self.db_path)
        db_success = self.db_manager.initialize_database()

        # Initialize email fetcher
        self.email_fetcher = ZeroInboxEmailFetcher(self.config, self.db_manager)

        # Initialize categorization agent
        self.categorization_agent = EmailCategorizationAgent(
            self.config, self.db_manager
        )

        return {"database_initialized": db_success, "components_ready": True}

    def fetch_emails(
        self,
        days_back: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        max_emails: Optional[int] = None,
    ) -> Dict[str, int]:
        """Fetch emails from Gmail and store in database."""
        if not self.email_fetcher:
            raise RuntimeError("Must run setup() first")

        # Prepare parameters
        kwargs = {}
        if days_back is not None:
            kwargs["days_back"] = days_back
        if from_date is not None:
            kwargs["from_date"] = from_date
        if to_date is not None:
            kwargs["to_date"] = to_date
        if max_emails is not None:
            kwargs["max_emails"] = max_emails

        # Fetch emails
        emails_fetched, emails_stored = self.email_fetcher.fetch_and_store_emails(
            **kwargs
        )

        return {
            "fetched": emails_fetched,
            "stored": emails_stored,
            "duplicates_skipped": emails_fetched - emails_stored,
        }

    def categorize_emails(
        self, batch_size: int = 5, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Categorize uncategorized emails using AI."""
        if not self.categorization_agent:
            raise RuntimeError("Must run setup() first")

        # Get uncategorized emails
        uncategorized_emails = self.categorization_agent.get_uncategorized_emails(
            limit=limit or batch_size
        )

        if not uncategorized_emails:
            return {"processed": 0, "stored": 0, "results": []}

        # Run batch categorization
        categorization_results = self.categorization_agent.categorize_emails_batch(
            uncategorized_emails, batch_size=batch_size
        )

        # Store results in database
        stored_count = 0
        if categorization_results:
            stored_count = self.categorization_agent.store_categorization_results(
                categorization_results
            )

        return {
            "processed": len(categorization_results),
            "stored": stored_count,
            "results": categorization_results,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get current categorization statistics."""
        if not self.categorization_agent:
            raise RuntimeError("Must run setup() first")

        return self.categorization_agent.get_categorization_stats()

    def get_llm_status(self) -> Dict[str, Dict[str, Any]]:
        """Get LLM provider status."""
        return validate_all_providers()

    def export_results(self, output_dir: str = "output/human_review") -> Dict[str, str]:
        """Export categorized emails to JSON for human review."""
        if not self.db_manager:
            raise RuntimeError("Must run setup() first")

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

        # Get statistics
        stats = self.get_stats()

        # Generate export filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_filename = f"zero_inbox_review_{timestamp}.json"
        export_path = os.path.join(output_dir, export_filename)

        # Create export data
        export_data = {
            "export_metadata": {
                "export_date": datetime.now().isoformat(),
                "total_emails": stats.get("total_emails", 0),
                "categorized_emails": stats.get("categorized_emails", 0),
                "pending_review": stats.get("categorized_emails", 0),
            },
            "emails": [],
        }

        # Add categorized emails if any exist
        if stats.get("categorized_emails", 0) > 0:
            # Get categorized emails from database
            session = self.db_manager.get_session()
            categorized_emails = session.query(Email).join(EmailCategory).all()

            for email in categorized_emails:
                for category in email.categories:
                    export_data["emails"].append(
                        {
                            "email_id": email.id,
                            "sender": email.sender,
                            "subject": email.subject,
                            "date": email.date_received.isoformat(),
                            "original_category": category.category,
                            "original_subcategory": category.subcategory,
                            "confidence": category.classification_confidence,
                            "reasoning": category.supporting_information,
                            "review_fields": {
                                "approved": None,
                                "corrected_category": None,
                                "corrected_subcategory": None,
                                "human_reasoning": None,
                            },
                        }
                    )

            session.close()

        # Write export file
        with open(export_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)

        return {
            "export_path": export_path,
            "emails_exported": len(export_data["emails"]),
        }

    def run(self, methods: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute specified methods in order with parameters.

        Args:
            methods: List of method names to execute. Defaults to ['setup', 'fetch_emails', 'categorize_emails']
            **kwargs: Parameters for specific methods, e.g. fetch_emails={'days_back': 7}

        Returns:
            Dict with results from each executed method
        """
        if methods is None:
            methods = ["setup", "fetch_emails", "categorize_emails"]

        results = {}

        for method_name in methods:
            if not hasattr(self, method_name):
                raise ValueError(f"Unknown method: {method_name}")

            method = getattr(self, method_name)
            method_params = kwargs.get(method_name, {})

            try:
                results[method_name] = method(**method_params)
            except Exception as e:
                results[method_name] = {"error": str(e)}

        return results


def main():
    """Example usage of the ZeroInboxAgent."""
    agent = ZeroInboxAgent()

    # # Example 1: Full pipeline
    print("Running full pipeline...")
    results = agent.run()
    print(f"Setup: {results['setup']['components_ready']}")
    print(f"Fetched: {results['fetch_emails']['fetched']} emails")
    print(f"Categorized: {results['categorize_emails']['processed']} emails")

    # # Example 2: Get statistics
    # print("\nGetting statistics...")
    # stats = agent.get_stats()
    # print(f"Total emails: {stats.get('total_emails', 0)}")
    # print(f"Categorized: {stats.get('categorized_emails', 0)}")

    # Example 3: Custom parameters
    # print("\nCustom fetch with date range...")
    # custom_results = agent.run(
    #     ["setup", "categorize_emails"],
    #     fetch_emails={"from_date": "2020-08-28", "to_date": "2020-08-30"},
    # )
    # print(f"Custom fetch result: {custom_results}")


if __name__ == "__main__":
    main()
