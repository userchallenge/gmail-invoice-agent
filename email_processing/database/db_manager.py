from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import html2text
import json
from datetime import datetime
from typing import List, Dict, Optional

from ..models.email_models import Base, Email, Category, Categorization, Summary


class EmailDatabaseManager:
    def __init__(self, db_path: str = "data/email_processing.db"):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = True
        self.html_converter.ignore_images = True
    
    def initialize_database(self):
        """Create all tables and populate initial categories."""
        Base.metadata.create_all(bind=self.engine)
        self._populate_categories()
    
    def _populate_categories(self):
        """Pre-populate categories table with information and action."""
        session = self.SessionLocal()
        
        # Check if categories already exist
        existing = session.query(Category).first()
        if existing:
            session.close()
            return
        
        categories = [
            Category(name="information"),
            Category(name="action")
        ]
        
        session.add_all(categories)
        session.commit()
        session.close()
    
    def store_email(self, email_data: Dict) -> None:
        """Store email data in the database."""
        session = self.SessionLocal()
        
        # Check if email already exists
        existing = session.query(Email).filter_by(email_id=email_data["id"]).first()
        if existing:
            session.close()
            return
        
        # Convert HTML body to markdown and clean text
        body_html = email_data.get("body", "")
        body_markdown = self.html_converter.handle(body_html)
        body_clean = self._clean_text(body_markdown)
        
        # Parse email date
        email_date = datetime.strptime(email_data["date"], "%Y-%m-%d %H:%M:%S") if email_data.get("date") else datetime.now()
        
        email = Email(
            email_id=email_data["id"],
            date=email_date,
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_markdown=body_markdown,
            body_clean=body_clean,
            pdf_text=email_data.get("pdf_text", ""),
            raw_email=json.dumps(email_data)
        )
        
        session.add(email)
        session.commit()
        session.close()
    
    def _clean_text(self, text: str) -> str:
        """Clean text by removing extra whitespace and normalizing."""
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        return '\n'.join(lines)
    
    def get_uncategorized_emails(self) -> List[Email]:
        """Get emails that haven't been categorized yet."""
        session = self.SessionLocal()
        emails = session.query(Email).filter(Email.category_id.is_(None)).all()
        session.close()
        return emails
    
    def store_categorization(self, email_id: str, category_name: str, agent_name: str, 
                           model_version: str, ai_reasoning: str) -> None:
        """Store categorization result."""
        session = self.SessionLocal()
        
        # Get category ID
        category = session.query(Category).filter_by(name=category_name).first()
        if not category:
            session.close()
            return
        
        # Update email category
        email = session.query(Email).filter_by(email_id=email_id).first()
        if email:
            email.category_id = category.category_id
        
        # Store categorization
        categorization = Categorization(
            email_id=email_id,
            agent_name=agent_name,
            model_version=model_version,
            ai_reasoning=ai_reasoning
        )
        
        session.add(categorization)
        session.commit()
        session.close()
    
    def get_information_emails_without_summary(self) -> List[Email]:
        """Get information emails that don't have summaries yet."""
        session = self.SessionLocal()
        
        # Get information category
        info_category = session.query(Category).filter_by(name="information").first()
        if not info_category:
            session.close()
            return []
        
        # Find emails with information category but no summaries
        emails = session.query(Email).filter(
            Email.category_id == info_category.category_id,
            ~Email.summaries.any()
        ).all()
        
        session.close()
        return emails
    
    def store_summary(self, email_id: str, email_summary: str,
                     ai_reasoning: str, agent_name: str, model_version: str) -> None:
        """Store summary result."""
        session = self.SessionLocal()
        
        summary = Summary(
            email_id=email_id,
            agent_name=agent_name,
            model_version=model_version,
            summary=email_summary,
            ai_reasoning=ai_reasoning
        )
        
        session.add(summary)
        session.commit()
        session.close()
    
    def get_processing_stats(self) -> Dict:
        """Get processing statistics."""
        session = self.SessionLocal()
        
        total_emails = session.query(Email).count()
        categorized_emails = session.query(Email).filter(Email.category_id.isnot(None)).count()
        summarized_emails = session.query(Summary).count()
        
        session.close()
        
        return {
            "total_emails": total_emails,
            "categorized_emails": categorized_emails,
            "summarized_emails": summarized_emails
        }
    
    def delete_all_tables(self) -> None:
        """Empty all database tables and re-populate categories."""
        session = self.SessionLocal()
        
        # Delete all data from tables
        session.query(Summary).delete()
        session.query(Categorization).delete()
        session.query(Email).delete()
        session.query(Category).delete()
        
        session.commit()
        session.close()
        
        # Re-populate categories
        self._populate_categories()
    
    def delete_result_tables(self) -> None:
        """Clear categorizations and summaries tables, reset email categories."""
        session = self.SessionLocal()
        
        # Delete processing results
        session.query(Summary).delete()
        session.query(Categorization).delete()
        
        # Reset email category_id to NULL
        session.query(Email).update({Email.category_id: None})
        
        session.commit()
        session.close()
    
    def delete_result_table(self, table_name: str) -> None:
        """Clear specific result table."""
        session = self.SessionLocal()
        
        if table_name == "categorizations":
            session.query(Categorization).delete()
            # Reset email category_id to NULL
            session.query(Email).update({Email.category_id: None})
        elif table_name == "summaries":
            session.query(Summary).delete()
        else:
            session.close()
            raise ValueError(f"Invalid table name: {table_name}. Must be 'categorizations' or 'summaries'")
        
        session.commit()
        session.close()
    
    def get_table_counts(self) -> Dict[str, int]:
        """Get count of records in each table."""
        session = self.SessionLocal()
        
        counts = {
            "emails": session.query(Email).count(),
            "categories": session.query(Category).count(),
            "categorizations": session.query(Categorization).count(),
            "summaries": session.query(Summary).count()
        }
        
        session.close()
        return counts
    
    def get_connection(self):
        """Get direct database connection for custom queries with Pandas."""
        return self.engine