"""
Email Categorization Agent using Atomic Agents Framework
Categorizes emails into Zero Inbox categories using configured LLM providers
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import Field

from atomic_agents.agents.atomic_agent import AtomicAgent, AgentConfig
from atomic_agents.base.base_io_schema import BaseIOSchema
from atomic_agents.context.system_prompt_generator import SystemPromptGenerator, BaseDynamicContextProvider

from models.zero_inbox_models import DatabaseManager, Email, EmailCategory
from llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)


class CategoryRulesContextProvider(BaseDynamicContextProvider):
    """Context provider for email category rules"""
    
    def __init__(self, category_rules: str):
        super().__init__("Category Rules")
        self.category_rules = category_rules
    
    def get_info(self) -> str:
        return self.category_rules


class EmailCategorizationInput(BaseIOSchema):
    """Input schema for email categorization. Contains the email content, sender, and subject needed for categorization analysis by the AI agent."""
    
    email_content: str = Field(
        ..., 
        description="The full email content including body and any PDF attachments"
    )
    sender: str = Field(
        ..., 
        description="Email sender address"
    )
    subject: str = Field(
        ..., 
        description="Email subject line"
    )


class EmailCategorizationOutput(BaseIOSchema):
    """Output schema for email categorization results. Contains the categorization results including primary category, subcategory, confidence score, and reasoning for the classification."""
    
    category: str = Field(
        ..., 
        description="Primary category: Other, Reading, Review, or Task"
    )
    subcategory: str = Field(
        ..., 
        description="Specific subcategory like Advertising, Rest, Job search, etc."
    )
    confidence: float = Field(
        ..., 
        description="Confidence score between 0.0 and 1.0 for this categorization",
        ge=0.0, 
        le=1.0
    )
    reasoning: str = Field(
        ..., 
        description="Brief explanation for why this email was categorized this way"
    )


class EmailCategorizationAgent:
    """
    Email categorization agent using Atomic Agents framework
    Supports multiple LLM providers through configuration
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.atomic_agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Atomic Agent with configured LLM provider"""
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            provider = llm_config.get('provider', 'gemini')
            models = llm_config.get('models', {})
            model = models.get(provider, 'gemini-2.0-flash')
            parameters = llm_config.get('parameters', {})
            
            logger.info(f"Initializing categorization agent with {provider} ({model})")
            
            # Create LLM client
            client = LLMClientFactory.create_client(provider, model, parameters)
            
            # Create system prompt generator
            system_prompt_generator = self._create_system_prompt_generator()
            
            # Filter parameters based on provider
            filtered_parameters = self._filter_parameters_for_provider(provider, parameters)
            
            # Create agent configuration following atomic-agents design
            agent_config = AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                model_api_parameters=filtered_parameters
            )
            
            # Initialize atomic agent
            self.atomic_agent = AtomicAgent[EmailCategorizationInput, EmailCategorizationOutput](agent_config)
            
            logger.info("✅ Email categorization agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize categorization agent: {e}")
            raise RuntimeError(f"Could not initialize email categorization agent: {e}")
    
    def _filter_parameters_for_provider(self, provider: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter API parameters based on provider capabilities"""
        if provider == 'gemini':
            # Gemini supports different parameter names/structures
            filtered = {}
            # Skip temperature and max_tokens for now - Gemini handles these differently
            # Add only supported parameters here
            return filtered
        elif provider == 'openai':
            # OpenAI supports standard parameters
            return parameters
        elif provider == 'claude':
            # Claude supports standard parameters 
            return parameters
        else:
            # Default to empty parameters for unknown providers
            return {}
    
    def _create_system_prompt_generator(self) -> SystemPromptGenerator:
        """Create system prompt with category rules and instructions"""
        
        # Generate category rules from config
        category_rules = self._generate_category_rules_from_config()
        
        # Get valid combinations for validation
        self.valid_combinations = self._get_valid_combinations_from_config()
        
        # Create context provider for category rules
        category_context_provider = CategoryRulesContextProvider(category_rules)
        
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert email categorization assistant for a Zero Inbox system.",
                "Your job is to analyze emails and categorize them into specific categories and subcategories.",
                "You must ONLY use the exact category/subcategory combinations provided in the rules.",
                "You should be accurate but also practical - help the user achieve inbox zero."
            ],
            steps=[
                "1. Read the email content, sender, and subject carefully",
                "2. Analyze the content for key indicators and patterns", 
                "3. Match against the category definitions provided",
                "4. Choose the most appropriate category and subcategory from the VALID COMBINATIONS ONLY",
                "5. Assign a confidence score based on how certain you are",
                "6. Provide clear reasoning for your categorization decision"
            ],
            output_instructions=[
                "Return the categorization in the exact format specified",
                "You MUST use only the valid category/subcategory combinations listed in the rules",
                "Invalid combinations will be rejected - stick to the provided options",
                "Confidence should reflect your certainty (0.8+ for high confidence)",
                "Reasoning should be concise but informative"
            ],
            context_providers={"category_rules": category_context_provider}
        )
        
        return system_prompt_generator
    
    def _generate_category_rules_from_config(self) -> str:
        """Generate category rules string from config structure"""
        categorization_config = self.config.get('categorization', {})
        categories = categorization_config.get('categories', {})
        
        rules = ["VALID CATEGORY/SUBCATEGORY COMBINATIONS:\n"]
        
        for category, category_data in categories.items():
            subcategories = category_data.get('subcategories', {})
            rules.append(f"\n{category.upper()} CATEGORY:")
            
            for subcategory, subcategory_data in subcategories.items():
                description = subcategory_data.get('description', '')
                keywords = subcategory_data.get('keywords', [])
                
                rules.append(f"  - {category}/{subcategory}: {description}")
                if keywords:
                    rules.append(f"    Keywords: {', '.join(keywords)}")
        
        rules.append("\nIMPORTANT: You MUST use ONLY these exact category/subcategory combinations. No other combinations are valid.")
        
        return '\n'.join(rules)
    
    def _get_valid_combinations_from_config(self) -> set:
        """Extract valid category/subcategory combinations from config"""
        valid_combinations = set()
        categorization_config = self.config.get('categorization', {})
        categories = categorization_config.get('categories', {})
        
        for category, category_data in categories.items():
            subcategories = category_data.get('subcategories', {})
            for subcategory in subcategories.keys():
                valid_combinations.add((category, subcategory))
        
        return valid_combinations
    
    def categorize_email(self, email: Email) -> Optional[EmailCategorizationOutput]:
        """
        Categorize a single email using the atomic agent
        
        Args:
            email: Email object from database
            
        Returns:
            EmailCategorizationOutput with categorization results, or None if failed
        """
        try:
            # Prepare email content for analysis
            email_content = email.body
            if email.pdf_content:
                email_content += f"\n\n--- PDF ATTACHMENT CONTENT ---\n{email.pdf_content}"
            
            # Create input
            categorization_input = EmailCategorizationInput(
                email_content=email_content[:3000],  # Limit content length
                sender=email.sender,
                subject=email.subject
            )
            
            # Run categorization
            logger.debug(f"Categorizing email: {email.subject[:50]}...")
            result = self.atomic_agent.run(categorization_input)
            
            # Validate result against config
            if not self._validate_categorization_result(result):
                logger.warning(f"Invalid categorization {result.category}/{result.subcategory} - using fallback")
                result = self._get_fallback_categorization()
            
            logger.debug(f"✅ Categorized as {result.category}/{result.subcategory} (confidence: {result.confidence:.2f})")
            return result
            
        except Exception as e:
            logger.error(f"Failed to categorize email {email.id}: {e}")
            return None
    
    def _validate_categorization_result(self, result: EmailCategorizationOutput) -> bool:
        """Validate that the categorization result uses valid combinations from config"""
        combination = (result.category, result.subcategory)
        return combination in getattr(self, 'valid_combinations', set())
    
    def _get_fallback_categorization(self) -> EmailCategorizationOutput:
        """Return fallback categorization for invalid results"""
        return EmailCategorizationOutput(
            category="Other",
            subcategory="Rest",
            confidence=0.1,
            reasoning="Fallback categorization due to invalid category/subcategory combination"
        )
    
    def categorize_emails_batch(self, emails: List[Email], batch_size: int = 5) -> List[Dict]:
        """
        Categorize multiple emails in batches
        
        Args:
            emails: List of Email objects to categorize
            batch_size: Number of emails to process at once
            
        Returns:
            List of dictionaries with email_id and categorization results
        """
        results = []
        
        for i in range(0, len(emails), batch_size):
            batch = emails[i:i + batch_size]
            logger.info(f"Processing categorization batch {i//batch_size + 1}/{(len(emails) + batch_size - 1)//batch_size}")
            
            for email in batch:
                try:
                    categorization = self.categorize_email(email)
                    if categorization:
                        results.append({
                            'email_id': email.id,
                            'email_gmail_id': email.email_id,
                            'category': categorization.category,
                            'subcategory': categorization.subcategory,
                            'confidence': categorization.confidence,
                            'reasoning': categorization.reasoning
                        })
                    else:
                        logger.warning(f"Failed to categorize email {email.id}")
                        
                except Exception as e:
                    logger.error(f"Error processing email {email.id}: {e}")
                    continue
        
        return results
    
    def store_categorization_results(self, results: List[Dict]) -> int:
        """
        Store categorization results in database
        
        Args:
            results: List of categorization results from categorize_emails_batch
            
        Returns:
            Number of results successfully stored
        """
        stored_count = 0
        
        try:
            session = self.db_manager.get_session()
            
            for result in results:
                try:
                    # Check if categorization already exists
                    existing = session.query(EmailCategory).filter(
                        EmailCategory.email_id == result['email_id']
                    ).first()
                    
                    if existing:
                        logger.debug(f"Email {result['email_id']} already categorized, skipping")
                        continue
                    
                    # Create new categorization record
                    category_record = EmailCategory(
                        email_id=result['email_id'],
                        category=result['category'],
                        subcategory=result['subcategory'],
                        category_description=f"Categorized as {result['category']}/{result['subcategory']}",
                        agent_action=f"Email categorization with confidence {result['confidence']:.2f}",
                        supporting_information=result['reasoning'],
                        classification_confidence=result['confidence'],
                        classified_by='EmailCategorizationAgent'
                    )
                    
                    session.add(category_record)
                    stored_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to store categorization for email {result.get('email_id')}: {e}")
                    continue
            
            session.commit()
            session.close()
            
            logger.info(f"✅ Stored {stored_count}/{len(results)} categorization results")
            return stored_count
            
        except Exception as e:
            logger.error(f"Failed to store categorization results: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return 0
    
    def get_uncategorized_emails(self, limit: int = 50) -> List[Email]:
        """
        Get emails that haven't been categorized yet
        
        Args:
            limit: Maximum number of emails to return
            
        Returns:
            List of uncategorized Email objects
        """
        try:
            session = self.db_manager.get_session()
            
            # Find emails without categories (excluding template records)
            uncategorized = session.query(Email).outerjoin(EmailCategory).filter(
                EmailCategory.email_id == None
            ).order_by(Email.date_received.desc()).limit(limit).all()
            
            # Detach from session
            result = []
            for email in uncategorized:
                session.expunge(email)
                result.append(email)
            
            session.close()
            return result
            
        except Exception as e:
            logger.error(f"Failed to get uncategorized emails: {e}")
            return []
    
    def get_categorization_stats(self) -> Dict:
        """Get statistics about email categorization"""
        try:
            session = self.db_manager.get_session()
            
            total_emails = session.query(Email).count()
            categorized_emails = session.query(EmailCategory).filter(
                EmailCategory.email_id > 0  # Exclude template records
            ).count()
            
            # Category breakdown
            category_stats = {}
            categories = session.query(
                EmailCategory.category,
                EmailCategory.subcategory
            ).filter(EmailCategory.email_id > 0).all()
            
            for category, subcategory in categories:
                key = f"{category}/{subcategory}"
                category_stats[key] = category_stats.get(key, 0) + 1
            
            session.close()
            
            return {
                'total_emails': total_emails,
                'categorized_emails': categorized_emails,
                'uncategorized_emails': total_emails - categorized_emails,
                'categorization_rate': categorized_emails / total_emails if total_emails > 0 else 0,
                'category_breakdown': category_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get categorization stats: {e}")
            return {}