from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Email(Base):
    __tablename__ = 'emails'
    
    email_id = Column(String, primary_key=True)
    date = Column(DateTime)
    sender = Column(String)
    subject = Column(String)
    body_markdown = Column(Text)
    body_clean = Column(Text)
    pdf_text = Column(Text, nullable=True)
    raw_email = Column(Text)
    category_id = Column(Integer, ForeignKey('categories.category_id'), nullable=True)
    
    # Relationships
    category = relationship("Category", back_populates="emails")
    categorizations = relationship("Categorization", back_populates="email")
    summaries = relationship("Summary", back_populates="email")
    tasks = relationship("Task", back_populates="email")


class Category(Base):
    __tablename__ = 'categories'
    
    category_id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, unique=True, nullable=False)
    
    # Relationships
    emails = relationship("Email", back_populates="category")


class Categorization(Base):
    __tablename__ = 'categorizations'
    
    categorization_id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey('emails.email_id'), nullable=False)
    agent_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    ai_reasoning = Column(Text, nullable=False)
    is_correct = Column(Boolean, nullable=True)
    feedback_reasoning = Column(Text, nullable=True)
    feedback_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    email = relationship("Email", back_populates="categorizations")


class Summary(Base):
    __tablename__ = 'summaries'
    
    summary_id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey('emails.email_id'), nullable=False)
    agent_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    ai_reasoning = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    is_correct = Column(Boolean, nullable=True)
    feedback_reasoning = Column(Text, nullable=True)
    feedback_date = Column(DateTime, nullable=True)
    
    # Relationships
    email = relationship("Email", back_populates="summaries")


class Task(Base):
    __tablename__ = 'tasks'
    
    task_id = Column(Integer, primary_key=True, autoincrement=True)
    email_id = Column(String, ForeignKey('emails.email_id'), nullable=False)
    agent_name = Column(String, nullable=False)
    model_version = Column(String, nullable=False)
    action_required = Column(Text, nullable=False)
    assigned_to = Column(String, nullable=True)
    due_date = Column(DateTime, nullable=True)
    priority = Column(String, nullable=True)
    ai_reasoning = Column(Text, nullable=False)
    generated_at = Column(DateTime, default=datetime.utcnow)
    is_correct = Column(Boolean, nullable=True)
    feedback_reasoning = Column(Text, nullable=True)
    feedback_date = Column(DateTime, nullable=True)
    
    # Relationships
    email = relationship("Email", back_populates="tasks")