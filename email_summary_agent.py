"""
Email Summary Agent using Atomic Agents Framework
Generates comprehensive summaries of email processing results for Phase 5
"""

import logging
from typing import Dict, List, Optional, Any
from pydantic import Field

from atomic_agents.agents.atomic_agent import AtomicAgent, AgentConfig
from atomic_agents.base.base_io_schema import BaseIOSchema
from atomic_agents.context.system_prompt_generator import SystemPromptGenerator, BaseDynamicContextProvider

from models.zero_inbox_models import DatabaseManager
from llm_client_factory import LLMClientFactory

logger = logging.getLogger(__name__)


class SummaryContextProvider(BaseDynamicContextProvider):
    """Context provider for summary generation rules"""
    
    def __init__(self, summary_rules: str):
        super().__init__("Summary Rules")
        self.summary_rules = summary_rules
    
    def get_info(self) -> str:
        return self.summary_rules


class EmailSummaryInput(BaseIOSchema):
    """Input schema for email summary generation. Contains processing statistics, category breakdown, and results needed for comprehensive summary generation."""
    
    time_period: str = Field(
        ...,
        description="Time period of the email processing session"
    )
    processing_stats: Dict[str, Any] = Field(
        ...,
        description="Overall processing statistics including total emails, categorized, etc."
    )
    category_breakdown: Dict[str, int] = Field(
        ...,
        description="Breakdown of emails by category/subcategory combinations"
    )
    action_results: List[Dict[str, Any]] = Field(
        ...,
        description="List of action results from executed actions"
    )
    errors_encountered: List[str] = Field(
        default_factory=list,
        description="List of errors encountered during processing"
    )


class EmailSummaryOutput(BaseIOSchema):
    """Output schema for email processing summary. Contains comprehensive formatted summary of the entire email processing session including statistics, results, and recommendations."""
    
    comprehensive_summary: str = Field(
        ...,
        description="Complete formatted summary of email processing results"
    )
    processing_success_rate: float = Field(
        ...,
        description="Success rate of processing as a percentage",
        ge=0.0,
        le=100.0
    )
    recommendations: List[str] = Field(
        ...,
        description="List of recommended next steps based on processing results"
    )


class EmailSummaryAgent:
    """
    Email summary agent using Atomic Agents framework
    Generates comprehensive summaries of email processing results
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.atomic_agent = None
        self._initialize_agent()
    
    def _initialize_agent(self):
        """Initialize the Atomic Agent for summary generation"""
        try:
            # Get LLM configuration
            llm_config = self.config.get('llm', {})
            provider = llm_config.get('provider', 'gemini')
            models = llm_config.get('models', {})
            model = models.get(provider, 'gemini-2.0-flash')
            parameters = llm_config.get('parameters', {})
            
            logger.info(f"Initializing summary agent with {provider} ({model})")
            
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
            self.atomic_agent = AtomicAgent[EmailSummaryInput, EmailSummaryOutput](agent_config)
            
            logger.info("✅ Email summary agent initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize summary agent: {e}")
            raise RuntimeError(f"Could not initialize email summary agent: {e}")
    
    def _filter_parameters_for_provider(self, provider: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Filter API parameters based on provider capabilities"""
        if provider == 'gemini':
            return {}
        elif provider in ['openai', 'claude']:
            return parameters
        else:
            return {}
    
    def _create_system_prompt_generator(self) -> SystemPromptGenerator:
        """Create system prompt for summary generation"""
        
        summary_rules = """
        EMAIL PROCESSING SUMMARY GENERATION RULES:
        
        You are tasked with generating a comprehensive summary of email processing results.
        
        Required Format:
        EMAIL PROCESSING SUMMARY
        ========================
        Time Period: {time_period}
        Total Emails Processed: {total_count}
        
        CATEGORY BREAKDOWN:
        - Category/Subcategory: {count} emails (with brief description)
        
        DETAILED RESULTS:
        For each processed email:
        - Sender: {sender}
        - Date: {date} (YYMMDD:HHMM format)
        - Subject: {subject}
        - Category: {category}/{subcategory}
        - Action Result: {action_summary}
        - Status: {success/error}
        
        PROCESSING SUMMARY:
        - Successfully Processed: {success_count}
        - Errors Encountered: {error_count}
        - Human Review Required: {review_count}
        
        RECOMMENDATIONS:
        - List specific next steps based on results
        - Highlight high-priority items requiring attention
        - Suggest improvements to processing workflow
        """
        
        summary_context_provider = SummaryContextProvider(summary_rules)
        
        system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an expert email processing summary generator for a Zero Inbox system.",
                "Your job is to create comprehensive, well-formatted summaries of email processing sessions.",
                "Focus on providing actionable insights and clear status reporting."
            ],
            steps=[
                "1. Analyze the processing statistics and results provided",
                "2. Format the summary according to the specified template",
                "3. Calculate success rates and identify key metrics",
                "4. Generate actionable recommendations based on results",
                "5. Ensure all data is presented clearly and accurately"
            ],
            output_instructions=[
                "Use the exact format specified in the summary rules",
                "Include all required sections with proper formatting",
                "Calculate accurate success rates as percentages",
                "Provide specific, actionable recommendations",
                "Keep the summary comprehensive but concise"
            ],
            context_providers={"summary_rules": summary_context_provider}
        )
        
        return system_prompt_generator
    
    def generate_summary(self, time_period: str, processing_stats: Dict[str, Any], 
                        category_breakdown: Dict[str, int], action_results: List[Dict[str, Any]], 
                        errors: List[str] = None) -> Optional[EmailSummaryOutput]:
        """Generate comprehensive summary of email processing results"""
        try:
            # Create input
            summary_input = EmailSummaryInput(
                time_period=time_period,
                processing_stats=processing_stats,
                category_breakdown=category_breakdown,
                action_results=action_results,
                errors_encountered=errors or []
            )
            
            # Run summary generation
            logger.debug("Generating email processing summary...")
            result = self.atomic_agent.run(summary_input)
            
            logger.debug("✅ Summary generated successfully")
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return None


class SimpleSummaryGenerator:
    """
    Simple summary generator that provides working summaries
    (fallback for atomic agents compatibility issues)
    """
    
    def __init__(self, config: Dict, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
    
    def generate_summary(self, time_period: str, processing_stats: Dict[str, Any], 
                        category_breakdown: Dict[str, int], action_results: List[Dict[str, Any]], 
                        errors: List[str] = None) -> Dict[str, Any]:
        """Generate simple summary of email processing results"""
        try:
            errors = errors or []
            
            # Calculate success metrics
            total_emails = processing_stats.get('total_emails', 0)
            categorized_emails = processing_stats.get('categorized_emails', 0)
            actions_processed = len(action_results)
            error_count = len(errors)
            
            success_rate = (categorized_emails / total_emails * 100) if total_emails > 0 else 0
            
            # Build category breakdown text
            category_text = ""
            for category_combo, count in category_breakdown.items():
                category_text += f"- {category_combo}: {count} emails\n"
            
            # Build detailed results text
            detailed_results = ""
            for i, action_result in enumerate(action_results[:10]):  # Limit to first 10 for brevity
                result_data = action_result.get('action_result', {})
                detailed_results += f"- Action {i+1}: {action_result.get('action_type', 'Unknown')} - {result_data}\n"
            
            if len(action_results) > 10:
                detailed_results += f"... and {len(action_results) - 10} more results\n"
            
            # Generate recommendations
            recommendations = []
            if error_count > 0:
                recommendations.append(f"Review {error_count} errors encountered during processing")
            if actions_processed > 0:
                recommendations.append(f"Review {actions_processed} processed actions for human validation")
            if success_rate < 90:
                recommendations.append("Consider reviewing categorization rules for improved accuracy")
            
            # Format comprehensive summary
            comprehensive_summary = f"""EMAIL PROCESSING SUMMARY
========================
Time Period: {time_period}
Total Emails Processed: {total_emails}

CATEGORY BREAKDOWN:
{category_text}

DETAILED RESULTS:
{detailed_results}

PROCESSING SUMMARY:
- Successfully Processed: {categorized_emails}
- Actions Executed: {actions_processed}  
- Errors Encountered: {error_count}
- Success Rate: {success_rate:.1f}%

RECOMMENDATIONS:
{chr(10).join(f'- {rec}' for rec in recommendations) if recommendations else '- All processing completed successfully'}
"""
            
            return {
                "comprehensive_summary": comprehensive_summary,
                "processing_success_rate": success_rate,
                "recommendations": recommendations
            }
            
        except Exception as e:
            logger.error(f"Failed to generate simple summary: {e}")
            return {
                "comprehensive_summary": f"Summary generation failed: {e}",
                "processing_success_rate": 0.0,
                "recommendations": ["Fix summary generation error"]
            }