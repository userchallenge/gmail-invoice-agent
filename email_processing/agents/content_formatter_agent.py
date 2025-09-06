import os
import instructor
import anthropic
from atomic_agents import AtomicAgent, AgentConfig
from atomic_agents.context import SystemPromptGenerator, ChatHistory

from ..schemas.agent_schemas import ContentFormatterInputSchema, ContentFormatterOutputSchema


class ContentFormatterAgent:
    def __init__(self):
        self.client = instructor.from_anthropic(
            anthropic.Anthropic(api_key=os.getenv("CLAUDE_API_KEY"))
        )

        self.system_prompt_generator = SystemPromptGenerator(
            background=[
                "Format email summaries into professional, organized categories.",
                "Create crisp, professional newsletter-style content without emojis.",
                "Group related content logically for easy scanning.",
            ],
            steps=[
                "Analyze email summaries and identify content themes.",
                "Categorize content into logical professional sections.",
                "Format each category with clear headings and bullet points.",
                "Maintain consistent, professional tone throughout.",
            ],
            output_instructions=[
                "Create content for the Information section only (do NOT include ## Information heading).",
                "Organize into logical subsections like: NEWSLETTERS & PUBLICATIONS, BUSINESS & FINANCE, TECHNOLOGY, AUTOMOTIVE, GOLF-RELATED, STREAMING & MEDIA, APPOINTMENTS, etc.",
                "Format subsection headings as **UPPERCASE HEADINGS** followed by a blank line.",
                "Use bullet points (•) for main items, with indented dashes (-) for details.",
                "CRITICAL: Always include blank line after headings before bullet points.",
                "Use **bold** for newsletter/source names and key items.",
                "Maintain professional, scannable format without emojis.",
                "Include sender information where relevant for context.",
            ],
        )

    def format_content(self, summaries_data: list) -> str:
        """Format email summaries into professional categorized content."""

        # Create fresh history for each formatting request
        history = ChatHistory()

        agent = AtomicAgent[ContentFormatterInputSchema, ContentFormatterOutputSchema](
            config=AgentConfig(
                client=self.client,
                model="claude-3-5-sonnet-20241022",
                system_prompt_generator=self.system_prompt_generator,
                history=history,
                model_api_parameters={"max_tokens": 2000},
            )
        )

        input_schema = ContentFormatterInputSchema(
            summaries=summaries_data
        )

        response = agent.run(input_schema)

        return response.formatted_content