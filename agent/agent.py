from google.adk.agents import Agent

from tools import perform_full_extraction_workflow

from ..prompt import ADK_AGENT_INSTRUCTION

root = Agent(
    name="web-scraping-agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Agent to perform web crawling and structured data extraction.",
    instruction=ADK_AGENT_INSTRUCTION,
    tools=[perform_full_extraction_workflow],
)
