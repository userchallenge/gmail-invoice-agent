import os
from datetime import datetime, date
from typing import List, Dict, Optional
from sqlalchemy import and_
from .database.db_manager import EmailDatabaseManager
from .models.email_models import Email, Task, Summary, Category
from .agents.content_formatter_agent import ContentFormatterAgent


class DailySummaryGenerator:
    def __init__(self, db_manager: Optional[EmailDatabaseManager] = None):
        self.db_manager = db_manager or EmailDatabaseManager()
        self.summaries_dir = "email_processing/summaries"
        
    def generate_daily_summary(self, target_date: date) -> str:
        """Generate a daily summary document for the given date."""
        # Ensure summaries directory exists
        os.makedirs(self.summaries_dir, exist_ok=True)
        
        # Generate document content
        content = self._create_document_content(target_date)
        
        # Save to file
        filename = f"emails_{target_date.strftime('%Y-%m-%d')}.md"
        filepath = os.path.join(self.summaries_dir, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return filepath
    
    def _create_document_content(self, target_date: date) -> str:
        """Create the markdown content for the daily summary."""
        date_str = target_date.strftime('%Y-%m-%d')
        
        # Get data for each section
        actions = self.get_actions_for_date(target_date)
        job_emails = self.get_job_search_emails_for_date(target_date)
        info_summaries = self.get_information_summaries_for_date(target_date)
        
        # Build document
        content = f"# Email & Newsletter Summary - {date_str}\n\n"
        
        # Actions section
        content += self._generate_actions_section(actions)
        
        # Job Search section  
        content += self._generate_job_search_section(job_emails)
        
        # Information section
        content += self._generate_information_section(info_summaries)
        
        return content
    
    def get_actions_for_date(self, target_date: date) -> List[Dict]:
        """Get all action tasks for a specific date."""
        session = self.db_manager.SessionLocal()
        
        try:
            # Get action category
            action_category = session.query(Category).filter_by(name="action").first()
            if not action_category:
                return []
            
            # Query emails with tasks from the target date
            results = session.query(Email, Task).join(Task).filter(
                and_(
                    Email.category_id == action_category.category_id,
                    Email.date >= datetime.combine(target_date, datetime.min.time()),
                    Email.date < datetime.combine(target_date, datetime.max.time())
                )
            ).all()
            
            actions = []
            for email, task in results:
                actions.append({
                    'email_id': email.email_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'email_date': email.date,
                    'action_required': task.action_required,
                    'assigned_to': task.assigned_to,
                    'due_date': task.due_date,
                    'priority': task.priority
                })
            
            return actions
            
        finally:
            session.close()
    
    def get_job_search_emails_for_date(self, target_date: date) -> List[Dict]:
        """Get all job search emails for a specific date."""
        session = self.db_manager.SessionLocal()
        
        try:
            # Get job_search category
            job_category = session.query(Category).filter_by(name="job_search").first()
            if not job_category:
                return []
            
            # Query job search emails from the target date
            emails = session.query(Email).filter(
                and_(
                    Email.category_id == job_category.category_id,
                    Email.date >= datetime.combine(target_date, datetime.min.time()),
                    Email.date < datetime.combine(target_date, datetime.max.time())
                )
            ).all()
            
            job_emails = []
            for email in emails:
                # Extract potential company name from sender domain
                company = self._extract_company_from_sender(email.sender)
                
                # Extract potential role from subject
                role = self._extract_role_from_subject(email.subject)
                
                job_emails.append({
                    'email_id': email.email_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'email_date': email.date,
                    'company': company,
                    'role': role
                })
            
            return job_emails
            
        finally:
            session.close()
    
    def get_information_summaries_for_date(self, target_date: date) -> List[Dict]:
        """Get all information email summaries for a specific date."""
        session = self.db_manager.SessionLocal()
        
        try:
            # Get information category
            info_category = session.query(Category).filter_by(name="information").first()
            if not info_category:
                return []
            
            # Query emails with summaries from the target date
            results = session.query(Email, Summary).join(Summary).filter(
                and_(
                    Email.category_id == info_category.category_id,
                    Email.date >= datetime.combine(target_date, datetime.min.time()),
                    Email.date < datetime.combine(target_date, datetime.max.time())
                )
            ).all()
            
            summaries = []
            for email, summary in results:
                summaries.append({
                    'email_id': email.email_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'email_date': email.date,
                    'summary': summary.summary
                })
            
            return summaries
            
        finally:
            session.close()
    
    def _generate_actions_section(self, actions: List[Dict]) -> str:
        """Generate the actions section of the document."""
        if not actions:
            return "## Actions\n*No action items found for this date.*\n\n"
        
        content = "## Actions\n"
        
        # Group actions by assignee
        actions_by_assignee = {}
        for action in actions:
            assignee = action['assigned_to'] or 'Unassigned'
            if assignee not in actions_by_assignee:
                actions_by_assignee[assignee] = []
            actions_by_assignee[assignee].append(action)
        
        # Generate content for each assignee
        for assignee, assignee_actions in actions_by_assignee.items():
            content += f"### {assignee}:\n"
            for action in assignee_actions:
                due_date = action['due_date'].strftime('%Y-%m-%d') if action['due_date'] else 'Not specified'
                priority = action['priority'] or 'Not specified'
                content += f"- **{action['action_required']}** - Due: {due_date} - Priority: {priority}\n"
            content += "\n"
        
        return content
    
    def _generate_job_search_section(self, job_emails: List[Dict]) -> str:
        """Generate the job search section of the document."""
        if not job_emails:
            return "## Job Search\n*No job opportunities found for this date.*\n\n"
        
        content = "## Job Search\n"
        
        # Group by company
        jobs_by_company = {}
        other_jobs = []
        
        for job in job_emails:
            company = job['company']
            if company and company != 'Unknown':
                if company not in jobs_by_company:
                    jobs_by_company[company] = []
                jobs_by_company[company].append(job)
            else:
                other_jobs.append(job)
        
        # Generate content for companies
        for company, company_jobs in jobs_by_company.items():
            content += f"### {company}:\n"
            for job in company_jobs:
                role = job['role'] or job['subject']
                date_str = job['email_date'].strftime('%Y-%m-%d')
                content += f"- **{role}** - Announced: {date_str}\n"
            content += "\n"
        
        # Generate content for other jobs
        if other_jobs:
            content += "### Other Job Opportunities:\n"
            for job in other_jobs:
                role = job['role'] or job['subject']
                date_str = job['email_date'].strftime('%Y-%m-%d')
                content += f"- **{role}** from {job['sender']} - Announced: {date_str}\n"
            content += "\n"
        
        return content
    
    def _generate_information_section(self, summaries: List[Dict]) -> str:
        """Generate professionally formatted information section using AI agent."""
        if not summaries:
            return "*No information emails found for this date.*\n\n"
        
        # Prepare data for ContentFormatterAgent
        summaries_data = []
        for summary in summaries:
            summaries_data.append({
                'summary': summary['summary'],
                'sender': summary['sender'],
                'subject': summary['subject'],
                'email_date': summary['email_date'].strftime('%Y-%m-%d')
            })
        
        # Use ContentFormatterAgent to format professionally
        formatter = ContentFormatterAgent()
        try:
            formatted_content = formatter.format_content(summaries_data)
            # Add the Information heading since agent doesn't include it
            return "## Information\n\n" + formatted_content + "\n\n"
        except Exception as e:
            # Fallback to basic format if agent fails
            content = "## Information\n\n"
            for summary in summaries:
                if summary['summary']:
                    content += f"- {summary['summary']}\n"
            content += "\n"
            return content
    
    def _extract_company_from_sender(self, sender: str) -> str:
        """Extract company name from sender email address."""
        if not sender or '@' not in sender:
            return 'Unknown'
        
        domain = sender.split('@')[1].lower()
        
        # Common company domain mappings
        company_mappings = {
            'must.se': 'MUST',
            'polisen.se': 'Polisen',
            'ework.se': 'Ework',
            'linkedin.com': 'LinkedIn',
            'noreply.linkedin.com': 'LinkedIn',
            'jobs.linkedin.com': 'LinkedIn'
        }
        
        if domain in company_mappings:
            return company_mappings[domain]
        
        # Extract company name from domain (remove common suffixes)
        domain_parts = domain.split('.')
        if len(domain_parts) >= 2:
            company = domain_parts[0]
            # Capitalize first letter
            return company.capitalize()
        
        return 'Unknown'
    
    def _extract_role_from_subject(self, subject: str) -> Optional[str]:
        """Extract potential role/position from email subject."""
        if not subject:
            return None
        
        # Common job-related keywords that might indicate role
        job_keywords = [
            'manager', 'engineer', 'developer', 'analyst', 'coordinator',
            'specialist', 'lead', 'senior', 'junior', 'director', 'consultant'
        ]
        
        subject_lower = subject.lower()
        
        # Look for job keywords in subject
        for keyword in job_keywords:
            if keyword in subject_lower:
                # Try to extract the role title around the keyword
                words = subject.split()
                for i, word in enumerate(words):
                    if keyword in word.lower():
                        # Take surrounding words to form role title
                        start = max(0, i-2)
                        end = min(len(words), i+3)
                        role_words = words[start:end]
                        role = ' '.join(role_words)
                        return role
        
        # If no specific role found, return the subject (truncated)
        return subject[:50] + "..." if len(subject) > 50 else subject