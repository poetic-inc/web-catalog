from google.adk.agents import Agent, SequentialAgent

from src.prompt import ANALYSIS_AGENT_PROMPT, EXTRACTION_AGENT_PROMPT
from src.tools import (
    perform_best_first_extraction_workflow,
    perform_bfs_extraction_workflow,
    perform_dfs_extraction_workflow,
    simple_crawl_tool,
)

# analysis_agent = Agent(
#     name="analysis_agent",
#     model="gemini-2.5-flash-preview-05-20",
#     description="Analyzes page content of the url from the user",
#     instruction=ANALYSIS_AGENT_PROMPT,
#     tools=[simple_crawl_tool],
#     output_key="page_analysis",
# )

root_agent = Agent(
    name="crawler_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Agent to perform page analysis, web crawling and structured data extraction using various strategies.",
    instruction=EXTRACTION_AGENT_PROMPT,
    tools=[
        simple_crawl_tool,
        perform_bfs_extraction_workflow,
        perform_dfs_extraction_workflow,
        perform_best_first_extraction_workflow,
    ],
)


# agent_pipeline = SequentialAgent(
#     name="agent_pipeline",
#     sub_agents=[analysis_agent, extraction_agent],
#     description="Executes a sequence of subagents for webpage analysis, extraction and formatting",
# )

# root_agent = agent_pipeline
