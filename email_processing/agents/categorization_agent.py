import os
import instructor
import anthropic
from atomic_agents import AtomicAgent, AgentConfig
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas.agent_schemas import (
    EmailCategorizationInputSchema,
    EmailCategorizationOutputSchema,
)


class EmailCategorizationAgent:
    def __init__(self):
        self.client = instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        )

        self.system_prompt_generator = SystemPromptGenerator(
            background=[
                "Categorize emails as 'information', 'action', or 'job_search'.",
                "Information: newsletters, ads, updates, general inquiries.",
                "Action: requests, questions, invoices, tasks, urgent issues.",
                "Job_search: job offers, position postings, recruiting emails.",
            ],
            steps=[
                "Read email content.",
                "Categorize as 'information', 'action', or 'job_search'.",
                "Provide brief reasoning.",
            ],
            output_instructions=[
                "Set category to 'information', 'action', or 'job_search'.",
                "Give short reasoning (1-2 sentences) on the format: Category: <category>. <reasoning>",
            ],
        )

    def categorize_email(self, email_data: dict) -> dict:
        """Categorize a single email using the atomic agent."""

        # Create fresh history for each email
        history = ChatHistory()

        agent = AtomicAgent[
            EmailCategorizationInputSchema, EmailCategorizationOutputSchema
        ](
            config=AgentConfig(
                client=self.client,
                model="claude-3-5-sonnet-20241022",
                system_prompt_generator=self.system_prompt_generator,
                history=history,
                model_api_parameters={"max_tokens": 1000},
            )
        )

        input_schema = EmailCategorizationInputSchema(
            email_id=email_data["email_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_clean=email_data["body_clean"],
            pdf_text=email_data.get("pdf_text", ""),
        )

        response = agent.run(input_schema)

        return {"category": response.category, "ai_reasoning": response.ai_reasoning}
