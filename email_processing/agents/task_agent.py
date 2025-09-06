import os
import instructor
import anthropic
from atomic_agents import AtomicAgent, AgentConfig
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas.agent_schemas import EmailTaskInputSchema, EmailTaskOutputSchema


class EmailTaskAgent:
    def __init__(self):
        self.client = instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        )

        self.system_prompt_generator = SystemPromptGenerator(
            background=[
                "Extract actionable tasks from action-category emails.",
                "Focus on what needs to be done, who should do it, when, and priority.",
            ],
            steps=[
                "Read email content.",
                "Identify specific actions required.",
                "Determine who should handle the task.",
                "Extract or estimate due dates.",
                "Assess priority based on urgency indicators.",
            ],
            output_instructions=[
                "Action Required: Specific actionable task (e.g., 'Pay invoice #12345', 'Schedule meeting with client').",
                "Assigned To: Who should handle this - if no specific person/team mentioned, use 'recipient'.",
                "Due Date: Extract date or estimate based on context, 'Not specified' if unclear.",
                "Priority: Low/Medium/High based on urgency words, deadlines, sender authority.",
                "Reasoning: Why these task details were identified.",
            ],
        )

    def analyze_task(self, email_data: dict) -> dict:
        """Analyze a single action email for task information using the atomic agent."""

        # Create fresh history for each email
        history = ChatHistory()

        agent = AtomicAgent[EmailTaskInputSchema, EmailTaskOutputSchema](
            config=AgentConfig(
                client=self.client,
                model="claude-3-5-sonnet-20241022",
                system_prompt_generator=self.system_prompt_generator,
                history=history,
                model_api_parameters={"max_tokens": 1000},
            )
        )

        input_schema = EmailTaskInputSchema(
            email_id=email_data["email_id"],
            sender=email_data["sender"],
            subject=email_data["subject"],
            body_clean=email_data["body_clean"],
            pdf_text=email_data.get("pdf_text", ""),
        )

        response = agent.run(input_schema)

        return {
            "action_required": response.action_required,
            "assigned_to": response.assigned_to,
            "due_date": response.due_date,
            "priority": response.priority,
            "ai_reasoning": response.ai_reasoning,
        }