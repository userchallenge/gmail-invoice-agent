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
from typing import Dict, List, Optional, Any

from models.zero_inbox_models import DatabaseManager, Email, EmailCategory
from zero_inbox_fetcher import ZeroInboxEmailFetcher
from email_categorization_agent import EmailCategorizationAgent
from email_action_agents import EmailActionOrchestrator
from llm_client_factory import validate_all_providers

logger = logging.getLogger(__name__)


class SimpleActionExecutor:
    """
    Simple action executor that provides working actions
    (fallback for atomic agents + Gemini compatibility issues)
    """

    def __init__(self, config: Dict, db_manager):
        self.config = config
        self.db_manager = db_manager

    def execute_action(
        self, email, category: str, subcategory: str
    ) -> Optional[Dict[str, Any]]:
        """Execute appropriate action based on category/subcategory"""
        try:
            action_type = f"{category}/{subcategory}"

            if action_type == "Other/Advertising":
                return self._execute_advertising_action(email, category, subcategory)
            elif action_type == "Other/Rest":
                return self._execute_rest_action(email, category, subcategory)
            elif action_type == "Review/Job search":
                return self._execute_job_search_action(email, category, subcategory)
            else:
                logger.warning(f"No action handler available for {action_type}")
                return None

        except Exception as e:
            logger.error(f"Failed to execute action for {category}/{subcategory}: {e}")
            return None

    def _execute_advertising_action(
        self, email, category: str, subcategory: str
    ) -> Dict[str, Any]:
        """Execute advertising analysis action"""
        config_data = (
            self.config.get("categorization", {})
            .get("categories", {})
            .get("Other", {})
            .get("subcategories", {})
            .get("Advertising", {})
        )
        keywords = config_data.get("keywords", [])

        content = email.body.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in content]

        key_indicators = (
            found_keywords
            if found_keywords
            else ["promotional content", "marketing email"]
        )
        reasoning = f"Email contains advertising content. Found indicators: {', '.join(key_indicators)}"
        sender_analysis = (
            f"Sender {email.sender} is sending promotional/marketing content"
        )

        return {
            "email_id": email.id,
            "action_type": f"{category}/{subcategory}",
            "action_result": {
                "categorization_reasoning": reasoning,
                "key_indicators": key_indicators,
                "sender_analysis": sender_analysis,
            },
        }

    def _execute_rest_action(
        self, email, category: str, subcategory: str
    ) -> Dict[str, Any]:
        """Execute rest category analysis action"""
        subject = email.subject
        sender = email.sender
        content = email.body[:200]  # First 200 chars

        summary = f"Email from {sender} about {subject}. Content preview: {content}..."
        reasoning = "This email doesn't fit into specific categories like job search, advertising, or specialized topics"
        suggested_action = "Review manually to determine appropriate handling"

        return {
            "email_id": email.id,
            "action_type": f"{category}/{subcategory}",
            "action_result": {
                "sender": sender,
                "subject": subject,
                "summary": summary,
                "reasoning": reasoning,
                "suggested_action": suggested_action,
            },
        }

    def _execute_job_search_action(
        self, email, category: str, subcategory: str
    ) -> Dict[str, Any]:
        """Execute job search analysis action"""
        config_data = (
            self.config.get("categorization", {})
            .get("categories", {})
            .get("Review", {})
            .get("subcategories", {})
            .get("Job search", {})
        )
        keywords = config_data.get("keywords", [])

        content = email.body.lower()
        found_keywords = [kw for kw in keywords if kw.lower() in content]

        companies_mentioned = []
        roles_identified = []

        target_companies = ["MUST", "Polisen", "Ework"]
        target_roles = ["IT Project manager", "Program Manager", "Change Manager"]

        for company in target_companies:
            if company.lower() in content:
                companies_mentioned.append(company)

        for role in target_roles:
            if role.lower() in content:
                roles_identified.append(role)

        if companies_mentioned or roles_identified:
            interest_level = "High"
            recommended_action = "Apply"
        elif found_keywords:
            interest_level = "Medium"
            recommended_action = "Research"
        else:
            interest_level = "Low"
            recommended_action = "Monitor"

        summary = f"Job opportunity email. Found {len(companies_mentioned)} target companies, {len(roles_identified)} target roles"

        return {
            "email_id": email.id,
            "action_type": f"{category}/{subcategory}",
            "action_result": {
                "companies_mentioned": companies_mentioned,
                "roles_identified": roles_identified,
                "domains_mentioned": found_keywords,
                "interest_level": interest_level,
                "summary": summary,
                "recommended_action": recommended_action,
            },
        }

    def store_action_result(self, action_result: Dict[str, Any]) -> bool:
        """Store action result in database"""
        try:
            from models.zero_inbox_models import AgentAction

            session = self.db_manager.get_session()

            action_record = AgentAction(
                email_id=action_result["email_id"],
                category=action_result["action_type"].split("/")[0],
                subcategory=action_result["action_type"].split("/")[1],
                action_performed=f"Simple action executed for {action_result['action_type']}",
                action_result=str(action_result["action_result"]),
                agent_name="SimpleActionExecutor",
                success=True,
            )

            session.add(action_record)
            session.commit()
            session.close()

            logger.debug(
                f"✅ Stored action result for email {action_result['email_id']}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to store action result: {e}")
            if "session" in locals():
                session.rollback()
                session.close()
            return False


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
        self.action_orchestrator = None

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

        # Initialize action orchestrator (using simple executor due to atomic agents + Gemini compatibility issues)
        logger.info(
            "Using SimpleActionExecutor due to atomic agents + Gemini docstring validation issues"
        )
        self.action_orchestrator = SimpleActionExecutor(self.config, self.db_manager)

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

    def execute_actions(
        self, batch_size: int = 5, limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """Execute actions on categorized emails using action agents."""
        if not self.action_orchestrator:
            raise RuntimeError("Must run setup() first")

        # Get categorized emails that need actions
        categorized_emails = self._get_categorized_emails_for_actions(
            limit or batch_size
        )

        if not categorized_emails:
            return {"processed": 0, "stored": 0, "results": []}

        # Execute actions in batches
        action_results = []
        stored_count = 0

        for i in range(0, len(categorized_emails), batch_size):
            batch = categorized_emails[i : i + batch_size]
            logger.info(
                f"Processing action batch {i//batch_size + 1}/{(len(categorized_emails) + batch_size - 1)//batch_size}"
            )

            for email_data in batch:
                try:
                    email, category, subcategory = email_data

                    # Execute appropriate action
                    action_result = self.action_orchestrator.execute_action(
                        email, category, subcategory
                    )

                    if action_result:
                        action_results.append(action_result)

                        # Store result in database
                        if self.action_orchestrator.store_action_result(action_result):
                            stored_count += 1
                    else:
                        logger.warning(f"No action executed for email {email.id}")

                except Exception as e:
                    logger.error(
                        f"Error processing action for email {email_data[0].id if email_data else 'unknown'}: {e}"
                    )
                    continue

        return {
            "processed": len(action_results),
            "stored": stored_count,
            "results": action_results,
        }

    def _get_categorized_emails_for_actions(self, limit: int = 50) -> List:
        """Get categorized emails that need actions executed"""
        try:
            if not self.db_manager:
                raise RuntimeError("Database manager not initialized")
            session = self.db_manager.get_session()

            # Get emails with categories that have action agents (Other/Advertising, Other/Rest, Review/Job search)
            target_combinations = [
                ("Other", "Advertising"),
                ("Other", "Rest"),
                ("Review", "Job search"),
            ]

            emails_for_actions = []

            for category, subcategory in target_combinations:
                # Find emails with this category/subcategory that haven't had actions executed
                categorized_emails = (
                    session.query(Email, EmailCategory)
                    .join(EmailCategory)
                    .filter(
                        EmailCategory.category == category,
                        EmailCategory.subcategory == subcategory,
                    )
                    .limit(limit)
                    .all()
                )

                for email, _ in categorized_emails:
                    # Check if action was already executed
                    from models.zero_inbox_models import AgentAction

                    existing_action = (
                        session.query(AgentAction)
                        .filter(
                            AgentAction.email_id == email.id,
                            AgentAction.category == category,
                            AgentAction.subcategory == subcategory,
                        )
                        .first()
                    )

                    if not existing_action:
                        emails_for_actions.append((email, category, subcategory))

            session.close()
            return emails_for_actions[:limit]

        except Exception as e:
            logger.error(f"Failed to get categorized emails for actions: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get current categorization statistics."""
        if not self.categorization_agent:
            raise RuntimeError("Must run setup() first")

        return self.categorization_agent.get_categorization_stats()

    def get_llm_status(self) -> Dict[str, Dict[str, Any]]:
        """Get LLM provider status."""
        return validate_all_providers()

    def export_results(self, output_dir: str = "output/human_review") -> Dict[str, Any]:
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
            methods = ["setup", "fetch_emails", "categorize_emails", "execute_actions"]

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
    print(f"Actions executed: {results['execute_actions']['processed']} emails")

    # # Example 2: Get statistics
    # print("\nGetting statistics...")
    # stats = agent.get_stats()
    # print(f"Total emails: {stats.get('total_emails', 0)}")
    # print(f"Categorized: {stats.get('categorized_emails', 0)}")

    # Example 3: Custom parameters
    print("\nCustom fetch with date range...")
    custom_results = agent.run(
        ["setup", "fetch_emails", "categorize_emails"],
        fetch_emails={"from_date": "2020-08-28", "to_date": "2020-08-30"},
    )
    print(f"Custom fetch result: {custom_results}")


if __name__ == "__main__":
    main()
