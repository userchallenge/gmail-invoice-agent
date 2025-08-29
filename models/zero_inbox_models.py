"""
Zero Inbox Agent - Database Models

SQLAlchemy models for the Zero Inbox email categorization and action system.
Follows the specifications from the implementation prompt.
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

Base = declarative_base()


class Email(Base):
    """
    Email Storage Table
    Stores Gmail emails with cleaned content and PDF extractions
    """
    __tablename__ = 'emails'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Gmail data
    email_id = Column(String(255), unique=True, nullable=False, index=True)  # Gmail message ID
    sender = Column(Text, nullable=False)
    subject = Column(Text, nullable=False)
    
    # Email content (cleaned and original)
    body = Column(Text, nullable=False)  # cleaned text content
    pdf_content = Column(Text)  # extracted PDF text
    html_content = Column(Text)  # original HTML
    
    # Timestamps
    date_received = Column(DateTime, nullable=False)
    date_processed = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # Attachment info
    has_attachments = Column(Boolean, default=False)
    attachment_count = Column(Integer, default=0)
    
    # Relationships
    categories = relationship("EmailCategory", back_populates="email", cascade="all, delete-orphan")
    actions = relationship("AgentAction", back_populates="email", cascade="all, delete-orphan")
    reviews = relationship("HumanReview", back_populates="email", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Email(id={self.id}, email_id='{self.email_id}', subject='{self.subject[:50]}...')>"


class EmailCategory(Base):
    """
    Email Categories Table
    Stores categorization results based on Zero Inbox structure
    """
    __tablename__ = 'email_categories'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign key to emails
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    
    # Category data (Other, Reading, Review, Task)
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=False, index=True)
    category_description = Column(Text)
    
    # Action and supporting info
    agent_action = Column(Text, nullable=False)  # specific action to perform
    supporting_information = Column(Text)  # keywords, rules, context
    
    # Classification metadata
    classification_confidence = Column(Float, default=0.0)
    classified_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    classified_by = Column(String(100), nullable=False)  # agent name
    
    # Relationship
    email = relationship("Email", back_populates="categories")
    
    def __repr__(self):
        return f"<EmailCategory(id={self.id}, category='{self.category}', subcategory='{self.subcategory}')>"


class AgentAction(Base):
    """
    Agent Actions Table
    Stores results from action agents processing categorized emails
    """
    __tablename__ = 'agent_actions'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign key to emails
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    
    # Category context
    category = Column(String(100), nullable=False, index=True)
    subcategory = Column(String(100), nullable=False, index=True)
    
    # Action execution details
    action_performed = Column(Text, nullable=False)  # specific action executed
    action_result = Column(Text, nullable=False)  # output/summary from agent
    
    # Processing metadata
    processed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    agent_name = Column(String(100), nullable=False)
    success = Column(Boolean, default=True)
    error_message = Column(Text)
    
    # Relationship
    email = relationship("Email", back_populates="actions")
    
    def __repr__(self):
        return f"<AgentAction(id={self.id}, agent='{self.agent_name}', success={self.success})>"


class HumanReview(Base):
    """
    Human Review Table
    Stores human feedback for categorization and action validation
    """
    __tablename__ = 'human_reviews'
    
    # Primary key
    id = Column(Integer, primary_key=True)
    
    # Foreign key to emails
    email_id = Column(Integer, ForeignKey('emails.id'), nullable=False, index=True)
    
    # Original AI categorization
    original_category = Column(String(100), nullable=False)
    original_subcategory = Column(String(100), nullable=False)
    
    # Human corrections
    reviewed_category = Column(String(100))
    reviewed_subcategory = Column(String(100))
    approved = Column(Boolean)
    human_reasoning = Column(Text)
    
    # Review metadata
    reviewed_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    reviewed_by = Column(String(100))
    
    # Relationship
    email = relationship("Email", back_populates="reviews")
    
    def __repr__(self):
        return f"<HumanReview(id={self.id}, approved={self.approved}, reviewed_by='{self.reviewed_by}')>"


# Create composite indexes for performance
Index('idx_email_category_subcategory', EmailCategory.category, EmailCategory.subcategory)
Index('idx_agent_action_category_subcategory', AgentAction.category, AgentAction.subcategory)
Index('idx_email_date_processed', Email.date_processed)
Index('idx_email_date_received', Email.date_received)


class DatabaseManager:
    """
    Database Manager for Zero Inbox system
    Handles database initialization, session management, and basic operations
    """
    
    def __init__(self, database_url: str = "sqlite:///data/zero_inbox.db"):
        self.database_url = database_url
        self.engine = None
        self.SessionLocal = None
        
    def initialize_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create database directory if it doesn't exist
            import os
            db_path = self.database_url.replace("sqlite:///", "")
            os.makedirs(os.path.dirname(db_path), exist_ok=True)
            
            # Create engine and session factory
            self.engine = create_engine(self.database_url, echo=False)
            self.SessionLocal = sessionmaker(bind=self.engine)
            
            # Create all tables
            Base.metadata.create_all(bind=self.engine)
            
            logger.info(f"✅ Zero Inbox database initialized: {self.database_url}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    def get_session(self):
        """Get a new database session"""
        if not self.SessionLocal:
            raise RuntimeError("Database not initialized. Call initialize_database() first.")
        return self.SessionLocal()
    
    def verify_schema(self):
        """Verify database schema is correctly created"""
        try:
            session = self.get_session()
            
            # Check if all tables exist by querying their counts
            tables_info = []
            
            email_count = session.query(Email).count()
            tables_info.append(f"emails: {email_count} records")
            
            category_count = session.query(EmailCategory).count()
            tables_info.append(f"email_categories: {category_count} records")
            
            action_count = session.query(AgentAction).count()
            tables_info.append(f"agent_actions: {action_count} records")
            
            review_count = session.query(HumanReview).count()
            tables_info.append(f"human_reviews: {review_count} records")
            
            session.close()
            
            logger.info("✅ Database schema verification successful:")
            for info in tables_info:
                logger.info(f"  - {info}")
            
            return True, tables_info
            
        except Exception as e:
            logger.error(f"❌ Database schema verification failed: {e}")
            return False, []
    
    def populate_initial_category_rules(self, category_rules: dict):
        """
        Populate initial category rules from configuration
        This creates template records for supported categories
        """
        try:
            session = self.get_session()
            
            # Check if we already have category templates
            existing_count = session.query(EmailCategory).filter(
                EmailCategory.email_id == 0  # Template records use email_id = 0
            ).count()
            
            if existing_count > 0:
                logger.info(f"Category templates already exist ({existing_count} found)")
                session.close()
                return True
            
            # Create template records for each category rule
            template_records = []
            for category_key, rules in category_rules.items():
                if '/' in category_key:
                    category, subcategory = category_key.split('/', 1)
                    
                    template = EmailCategory(
                        email_id=0,  # Special ID for templates
                        category=category,
                        subcategory=subcategory,
                        category_description=rules.get('supporting_info', ''),
                        agent_action=rules.get('action', ''),
                        supporting_information=str(rules),
                        classification_confidence=1.0,
                        classified_by='system_template'
                    )
                    template_records.append(template)
            
            # Insert template records
            session.add_all(template_records)
            session.commit()
            session.close()
            
            logger.info(f"✅ Created {len(template_records)} category rule templates")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to populate category rules: {e}")
            return False