import os
import sys

# Add the root directory to the Python path to import LLMClientFactory
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from atomic_agents import AtomicAgent, AgentConfig
from atomic_agents.context import SystemPromptGenerator, ChatHistory
from llm_client_factory import LLMClientFactory

from ..schemas.agent_schemas import EmailSummaryInputSchema, EmailSummaryOutputSchema


class EmailSummaryAgent:
    def __init__(self):
        self.client = LLMClientFactory.create_client(
            provider="gemini", model="gemini-2.0-flash"
        )

        self.system_prompt_generator = SystemPromptGenerator(
            background=[
                "You are an email summary agent.",
                "Your task is to analyze information emails and create concise summaries.",
                "Focus on the sender's purpose and the value provided to the recipient.",
            ],
            steps=[
                "Read the email content including subject, sender, body, and any PDF attachments.",
                "Identify the sender's purpose - why did they send this email?",
                "Determine what value this email provides for the recipient.",
                "Create clear, actionable insights about the email content.",
            ],
            output_instructions=[
                "Purpose should be 1-2 sentences explaining the sender's intent.",
                "Value for recipient should be 1-2 sentences explaining what the recipient gains.",
                "Reasoning should explain your analysis approach.",
                "Keep all responses concise and focused.",
            ],
        )

    def summarize_email(self, email_data: dict) -> dict:
        """Summarize a single information email using the atomic agent."""

        # Create fresh history for each email
        history = ChatHistory()

        agent = AtomicAgent[EmailSummaryInputSchema, EmailSummaryOutputSchema](
            config=AgentConfig(
                client=self.client,
                model="gemini-2.0-flash",
                system_prompt_generator=self.system_prompt_generator,
                history=history,
                # Gemini doesn't need max_tokens parameter
                # model_api_parameters={"max_output_tokens": 1000}
            )
        )

        input_schema = EmailSummaryInputSchema(
            email_id=email_data["email_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_clean=email_data["body_clean"],
            pdf_text=email_data.get("pdf_text", ""),
        )

        response = agent.run(input_schema)

        return {
            "purpose": response.purpose,
            "value_for_recipient": response.value_for_recipient,
            "ai_reasoning": response.ai_reasoning,
        }
