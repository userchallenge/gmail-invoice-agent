import os
import instructor
import anthropic
from atomic_agents import AtomicAgent, AgentConfig
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas.agent_schemas import EmailSummaryInputSchema, EmailSummaryOutputSchema


class EmailSummaryAgent:
    def __init__(self):
        self.client = instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        )

        self.system_prompt_generator = SystemPromptGenerator(
            background=[
                "Extract key information from emails in concise summaries.",
                "Focus on factual content: amounts, dates, names, actions.",
            ],
            steps=[
                "Read email content.",
                "Identify key facts and data points.",
                "Create concise summary with essential information only.",
            ],
            output_instructions=[
                "Email Summary: Key facts only - for job emails list all positions, for payments include what/when/amount/payee.",
                "Reasoning: Brief explanation of what information was extracted.",
            ],
        )

    def summarize_email(self, email_data: dict) -> dict:
        """Summarize a single information email using the atomic agent."""

        # Create fresh history for each email
        history = ChatHistory()

        agent = AtomicAgent[EmailSummaryInputSchema, EmailSummaryOutputSchema](
            config=AgentConfig(
                client=self.client,
                model="claude-3-5-sonnet-20241022",
                system_prompt_generator=self.system_prompt_generator,
                history=history,
                model_api_parameters={"max_tokens": 1000},
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
            "email_summary": response.email_summary,
            "ai_reasoning": response.ai_reasoning,
        }
