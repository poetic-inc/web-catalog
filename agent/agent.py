from google.adk.agents import Agent

from tools import (
    perform_bfs_extraction_workflow,
    perform_dfs_extraction_workflow,
    perform_best_first_extraction_workflow,
)
from prompt import ADK_AGENT_INSTRUCTION # Corrected relative import based on typical structure

root = Agent(
    name="web-scraping-agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Agent to perform web crawling and structured data extraction using various strategies.",
    instruction=ADK_AGENT_INSTRUCTION,
    tools=[
        perform_bfs_extraction_workflow,
        perform_dfs_extraction_workflow,
        perform_best_first_extraction_workflow,
    ],
)
