"""
Email Action Agents using Atomic Agents Framework
Executes specific actions on categorized emails following Phase 4 requirements
"""

import logging
from typing import Dict, List, Optional, Any
from pydantic import Field

from atomic_agents.agents.atomic_agent import AtomicAgent, AgentConfig
from atomic_agents.base.base_io_schema import BaseIOSchema
from atomic_agents.context.system_prompt_generator import SystemPromptGenerator, BaseDynamicContextProvider

from models.zero_inbox_models import DatabaseManager, Email, AgentAction
from llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)


class ActionRulesContextProvider(BaseDynamicContextProvider):
    """Context provider for action-specific rules"""
    
    def __init__(self, action_rules: str):
        super().__init__("Action Rules")
        self.action_rules = action_rules
    
    def get_info(self) -> str:
        return self.action_rules


class EmailActionInput(BaseIOSchema):
    """Input schema for email action processing. Contains the email information and categorization context needed for action execution by AI agents."""
    
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
    category: str = Field(
        ..., 
        description="Email category (Other, Reading, Review, Task)"
    )
    subcategory: str = Field(
        ..., 
        description="Email subcategory (Advertising, Rest, Job search, etc.)"
    )


class AdvertisingActionOutput(BaseIOSchema):
    """Output schema for advertising email analysis. Contains the analysis results for advertising emails including categorization reasoning and key indicators."""
    
    categorization_reasoning: str = Field(
        ..., 
        description="Detailed explanation for why this email was categorized as advertising"
    )
    key_indicators: List[str] = Field(
        ..., 
        description="List of specific elements that identify this email as advertising"
    )
    sender_analysis: str = Field(
        ..., 
        description="Brief analysis of the sender and their advertising intent"
    )


class RestActionOutput(BaseIOSchema):
    """Output schema for uncategorized email processing. Contains summary and analysis for emails that don't fit other specific categories."""
    
    sender: str = Field(
        ..., 
        description="Email sender address"
    )
    subject: str = Field(
        ..., 
        description="Email subject line"
    )
    summary: str = Field(
        ..., 
        description="One to two sentence summary about what the email consists of"
    )
    reasoning: str = Field(
        ..., 
        description="Explanation of why this email didn't fit into any of the other categories"
    )
    suggested_action: str = Field(
        ..., 
        description="Recommended action for handling this uncategorized email"
    )


class JobSearchActionOutput(BaseIOSchema):
    """Output schema for job search email analysis. Contains analysis of job-related emails for opportunities of interest based on target criteria."""
    
    companies_mentioned: List[str] = Field(
        ..., 
        description="List of any target companies found in the email"
    )
    roles_identified: List[str] = Field(
        ..., 
        description="List of any target roles found in the email"
    )
    domains_mentioned: List[str] = Field(
        ..., 
        description="List of relevant domains mentioned in the email"
    )
    interest_level: str = Field(
        ..., 
        description="Interest level: High, Medium, or Low based on target criteria"
    )
    summary: str = Field(
        ..., 
        description="Brief summary of the job opportunity for human review"
    )
    recommended_action: str = Field(
        ..., 
        description="Recommended action: Apply, Research, Monitor, or Ignore"
    )


class AdvertisingActionAgent:
    """
    Advertising action agent using Atomic Agents framework
    Analyzes advertising emails and provides categorization reasoning
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.atomic_agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Atomic Agent for advertising analysis"""
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            provider = llm_config.get('provider', 'gemini')
            models = llm_config.get('models', {})
            model = models.get(provider, 'gemini-2.0-flash')
            parameters = llm_config.get('parameters', {})
            
            logger.info(f"Initializing advertising action agent with {provider} ({model})")
            
            # Create LLM client
            client = LLMClientFactory.create_client(provider, model, parameters)
            
            # Create system prompt generator
            system_prompt_generator = self._create_system_prompt_generator()
            
            # Filter parameters based on provider
            filtered_parameters = self._filter_parameters_for_provider(provider, parameters)
            
            # Create agent configuration
            agent_config = AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                model_api_parameters=filtered_parameters
            )
            
            # Initialize atomic agent
            self.atomic_agent = AtomicAgent[EmailActionInput, AdvertisingActionOutput](agent_config)
            
            logger.info("✅ Advertising action agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize advertising action agent: {e}")
            raise RuntimeError(f"Could not initialize advertising action agent: {e}")
    
    def _filter_parameters_for_provider(self, provider: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter API parameters based on provider capabilities"""
        if provider == 'gemini':
            return {}
        elif provider in ['openai', 'claude']:
            return parameters
        else:
            return {}
    
    def _create_system_prompt_generator(self) -> SystemPromptGenerator:
        """Create system prompt for advertising analysis"""
        
        # Get action rules from config
        categorization_config = self.config.get('categorization', {})
        advertising_config = categorization_config.get('categories', {}).get('Other', {}).get('subcategories', {}).get('Advertising', {})
        
        action_rules = f"""
        ADVERTISING EMAIL ANALYSIS TASK:
        
        Action: {advertising_config.get('agent_action', 'Summarize the reasoning behind the categorization of this email.')}
        
        Description: {advertising_config.get('description', 'Offers and non-interesting advertising')}
        
        Keywords to look for: {', '.join(advertising_config.get('keywords', []))}
        
        Your task is to analyze advertising emails and provide detailed reasoning for the categorization.
        """
        
        action_context_provider = ActionRulesContextProvider(action_rules)
        
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert email analysis assistant specializing in advertising email categorization.",
                "Your job is to analyze emails already categorized as advertising and provide detailed reasoning.",
                "Focus on identifying specific advertising elements and sender intent."
            ],
            steps=[
                "1. Read the email content, sender, and subject carefully",
                "2. Identify specific advertising elements and patterns",
                "3. Analyze the sender's intent and advertising strategy", 
                "4. List key indicators that confirm this is advertising",
                "5. Provide comprehensive reasoning for the categorization"
            ],
            output_instructions=[
                "Provide detailed categorization reasoning explaining why this is advertising",
                "List specific key indicators found in the email",
                "Include analysis of the sender and their advertising intent",
                "Be thorough but concise in your analysis"
            ],
            context_providers={"action_rules": action_context_provider}
        )
        
        return system_prompt_generator
    
    def execute_action(self, email: Email, category: str, subcategory: str) -> Optional[AdvertisingActionOutput]:
        """Execute advertising analysis action on email"""
        try:
            # Prepare email content for analysis
            email_content = email.body
            if email.pdf_content:
                email_content += f"\n\n--- PDF ATTACHMENT CONTENT ---\n{email.pdf_content}"
            
            # Create input
            action_input = EmailActionInput(
                email_content=email_content[:3000],
                sender=email.sender,
                subject=email.subject,
                category=category,
                subcategory=subcategory
            )
            
            # Run action
            logger.debug(f"Executing advertising action on email: {email.subject[:50]}...")
            result = self.atomic_agent.run(action_input)
            
            logger.debug(f"✅ Advertising action completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute advertising action on email {email.id}: {e}")
            return None


class RestActionAgent:
    """
    Rest category action agent using Atomic Agents framework
    Summarizes uncategorized emails that don't fit other categories
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.atomic_agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Atomic Agent for rest category analysis"""
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            provider = llm_config.get('provider', 'gemini')
            models = llm_config.get('models', {})
            model = models.get(provider, 'gemini-2.0-flash')
            parameters = llm_config.get('parameters', {})
            
            logger.info(f"Initializing rest action agent with {provider} ({model})")
            
            # Create LLM client
            client = LLMClientFactory.create_client(provider, model, parameters)
            
            # Create system prompt generator
            system_prompt_generator = self._create_system_prompt_generator()
            
            # Filter parameters based on provider
            filtered_parameters = self._filter_parameters_for_provider(provider, parameters)
            
            # Create agent configuration
            agent_config = AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                model_api_parameters=filtered_parameters
            )
            
            # Initialize atomic agent
            self.atomic_agent = AtomicAgent[EmailActionInput, RestActionOutput](agent_config)
            
            logger.info("✅ Rest action agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize rest action agent: {e}")
            raise RuntimeError(f"Could not initialize rest action agent: {e}")
    
    def _filter_parameters_for_provider(self, provider: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter API parameters based on provider capabilities"""
        if provider == 'gemini':
            return {}
        elif provider in ['openai', 'claude']:
            return parameters
        else:
            return {}
    
    def _create_system_prompt_generator(self) -> SystemPromptGenerator:
        """Create system prompt for rest category analysis"""
        
        # Get action rules from config
        categorization_config = self.config.get('categorization', {})
        rest_config = categorization_config.get('categories', {}).get('Other', {}).get('subcategories', {}).get('Rest', {})
        
        action_rules = f"""
        REST CATEGORY EMAIL ANALYSIS TASK:
        
        Action: {rest_config.get('agent_action', 'Summarize a list of sender subject and a one-two sentence summary about what the email consists of including reasoning why it did not fit into any of the other categories')}
        
        Description: {rest_config.get('description', 'Anything that does not fit the other categories')}
        
        Your task is to summarize uncategorized emails and explain why they don't fit other categories.
        """
        
        action_context_provider = ActionRulesContextProvider(action_rules)
        
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert email analysis assistant specializing in uncategorized email processing.",
                "Your job is to summarize emails that don't fit into specific categories.",
                "Provide clear reasoning for why the email doesn't fit other categories."
            ],
            steps=[
                "1. Read the email content, sender, and subject carefully",
                "2. Create a concise summary of the email content",
                "3. Analyze why this email doesn't fit into other specific categories",
                "4. Suggest an appropriate action for handling this email",
                "5. Format the response according to requirements"
            ],
            output_instructions=[
                "Include the sender and subject information",
                "Provide a 1-2 sentence summary of email content", 
                "Explain reasoning for why it doesn't fit other categories",
                "Suggest an appropriate action for this email",
                "Be concise but informative"
            ],
            context_providers={"action_rules": action_context_provider}
        )
        
        return system_prompt_generator
    
    def execute_action(self, email: Email, category: str, subcategory: str) -> Optional[RestActionOutput]:
        """Execute rest category analysis action on email"""
        try:
            # Prepare email content for analysis
            email_content = email.body
            if email.pdf_content:
                email_content += f"\n\n--- PDF ATTACHMENT CONTENT ---\n{email.pdf_content}"
            
            # Create input
            action_input = EmailActionInput(
                email_content=email_content[:3000],
                sender=email.sender,
                subject=email.subject,
                category=category,
                subcategory=subcategory
            )
            
            # Run action
            logger.debug(f"Executing rest action on email: {email.subject[:50]}...")
            result = self.atomic_agent.run(action_input)
            
            logger.debug(f"✅ Rest action completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute rest action on email {email.id}: {e}")
            return None


class JobSearchActionAgent:
    """
    Job search action agent using Atomic Agents framework
    Analyzes job-related emails for opportunities of interest
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.atomic_agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Atomic Agent for job search analysis"""
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            provider = llm_config.get('provider', 'gemini')
            models = llm_config.get('models', {})
            model = models.get(provider, 'gemini-2.0-flash')
            parameters = llm_config.get('parameters', {})
            
            logger.info(f"Initializing job search action agent with {provider} ({model})")
            
            # Create LLM client
            client = LLMClientFactory.create_client(provider, model, parameters)
            
            # Create system prompt generator
            system_prompt_generator = self._create_system_prompt_generator()
            
            # Filter parameters based on provider
            filtered_parameters = self._filter_parameters_for_provider(provider, parameters)
            
            # Create agent configuration
            agent_config = AgentConfig(
                client=client,
                model=model,
                system_prompt_generator=system_prompt_generator,
                model_api_parameters=filtered_parameters
            )
            
            # Initialize atomic agent
            self.atomic_agent = AtomicAgent[EmailActionInput, JobSearchActionOutput](agent_config)
            
            logger.info("✅ Job search action agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize job search action agent: {e}")
            raise RuntimeError(f"Could not initialize job search action agent: {e}")
    
    def _filter_parameters_for_provider(self, provider: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter API parameters based on provider capabilities"""
        if provider == 'gemini':
            return {}
        elif provider in ['openai', 'claude']:
            return parameters
        else:
            return {}
    
    def _create_system_prompt_generator(self) -> SystemPromptGenerator:
        """Create system prompt for job search analysis"""
        
        # Get action rules from config
        categorization_config = self.config.get('categorization', {})
        job_search_config = categorization_config.get('categories', {}).get('Review', {}).get('subcategories', {}).get('Job search', {})
        
        target_keywords = job_search_config.get('keywords', [])
        
        action_rules = f"""
        JOB SEARCH EMAIL ANALYSIS TASK:
        
        Action: {job_search_config.get('agent_action', 'Identify roles and companies of interest and summarize a list for human review')}
        
        Description: {job_search_config.get('description', 'Review job listing')}
        
        Target Keywords: {', '.join(target_keywords)}
        
        Your task is to analyze job-related emails for opportunities that match the target criteria.
        Look for companies, roles, and domains of interest and assess the opportunity.
        """
        
        action_context_provider = ActionRulesContextProvider(action_rules)
        
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert job opportunity analysis assistant.",
                "Your job is to analyze job-related emails for opportunities of interest.",
                "Focus on identifying target companies, roles, and domains from the email content."
            ],
            steps=[
                "1. Read the email content, sender, and subject carefully",
                "2. Identify any target companies mentioned",
                "3. Identify any target roles mentioned",
                "4. Identify relevant domains or areas mentioned",
                "5. Assess the interest level based on target criteria",
                "6. Provide summary and recommended action"
            ],
            output_instructions=[
                "List any target companies found (use exact names from email)",
                "List any target roles identified (use exact titles from email)",
                "List relevant domains mentioned",
                "Assess interest level as High, Medium, or Low",
                "Provide brief summary for human review",
                "Recommend action: Apply, Research, Monitor, or Ignore"
            ],
            context_providers={"action_rules": action_context_provider}
        )
        
        return system_prompt_generator
    
    def execute_action(self, email: Email, category: str, subcategory: str) -> Optional[JobSearchActionOutput]:
        """Execute job search analysis action on email"""
        try:
            # Prepare email content for analysis
            email_content = email.body
            if email.pdf_content:
                email_content += f"\n\n--- PDF ATTACHMENT CONTENT ---\n{email.pdf_content}"
            
            # Create input
            action_input = EmailActionInput(
                email_content=email_content[:3000],
                sender=email.sender,
                subject=email.subject,
                category=category,
                subcategory=subcategory
            )
            
            # Run action
            logger.debug(f"Executing job search action on email: {email.subject[:50]}...")
            result = self.atomic_agent.run(action_input)
            
            logger.debug(f"✅ Job search action completed")
            return result
            
        except Exception as e:
            logger.error(f"Failed to execute job search action on email {email.id}: {e}")
            return None


class EmailActionOrchestrator:
    """
    Orchestrator for email action agents
    Routes emails to appropriate action agents based on category/subcategory
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        
        # Initialize action agents
        self.advertising_agent = AdvertisingActionAgent(config, db_manager)
        self.rest_agent = RestActionAgent(config, db_manager)
        self.job_search_agent = JobSearchActionAgent(config, db_manager)
    
    def execute_action(self, email: Email, category: str, subcategory: str) -> Optional[Dict[str, Any]]:
        """Execute appropriate action based on category/subcategory"""
        try:
            result = None
            action_type = f"{category}/{subcategory}"
            
            if action_type == "Other/Advertising":
                result = self.advertising_agent.execute_action(email, category, subcategory)
                if result:
                    return {
                        "email_id": email.id,
                        "action_type": action_type,
                        "action_result": {
                            "categorization_reasoning": result.categorization_reasoning,
                            "key_indicators": result.key_indicators,
                            "sender_analysis": result.sender_analysis
                        }
                    }
            
            elif action_type == "Other/Rest":
                result = self.rest_agent.execute_action(email, category, subcategory)
                if result:
                    return {
                        "email_id": email.id,
                        "action_type": action_type,
                        "action_result": {
                            "sender": result.sender,
                            "subject": result.subject,
                            "summary": result.summary,
                            "reasoning": result.reasoning,
                            "suggested_action": result.suggested_action
                        }
                    }
            
            elif action_type == "Review/Job search":
                result = self.job_search_agent.execute_action(email, category, subcategory)
                if result:
                    return {
                        "email_id": email.id,
                        "action_type": action_type,
                        "action_result": {
                            "companies_mentioned": result.companies_mentioned,
                            "roles_identified": result.roles_identified,
                            "domains_mentioned": result.domains_mentioned,
                            "interest_level": result.interest_level,
                            "summary": result.summary,
                            "recommended_action": result.recommended_action
                        }
                    }
            
            else:
                logger.warning(f"No action agent available for {action_type}")
                return None
            
        except Exception as e:
            logger.error(f"Failed to execute action for {category}/{subcategory}: {e}")
            return None
    
    def store_action_result(self, action_result: Dict[str, Any]) -> bool:
        """Store action result in database"""
        try:
            session = self.db_manager.get_session()
            
            action_record = AgentAction(
                email_id=action_result["email_id"],
                category=action_result["action_type"].split("/")[0],
                subcategory=action_result["action_type"].split("/")[1],
                action_performed=f"Action executed for {action_result['action_type']}",
                action_result=str(action_result["action_result"]),
                agent_name="EmailActionOrchestrator",
                success=True
            )
            
            session.add(action_record)
            session.commit()
            session.close()
            
            logger.debug(f"✅ Stored action result for email {action_result['email_id']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store action result: {e}")
            if 'session' in locals():
                session.rollback()
                session.close()
            return False