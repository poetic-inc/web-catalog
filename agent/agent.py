from google.adk.agents import Agent, LlmAgent, SequentialAgent

from src.prompt import (
    ANALYSIS_AGENT_PROMPT,
    COORDINATOR_AGENT_PROMPT,
    EXTRACTION_AGENT_PROMPT,
    FILTERING_AGENT_PROMPT,
)
from src.tools.crawling import (
    perform_best_first_extraction_workflow,
    perform_bfs_extraction_workflow,
    perform_dfs_extraction_workflow,
)
from src.tools.filters import (
    content_type_filter_tool,
    domain_filter_tool,
    url_filter_tool,
)
from src.tools.misc import simple_crawl_tool

analysis_agent = LlmAgent(
    name="analysis_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Analyzes page of the url and returns detailed analysis of a page content",
    instruction=ANALYSIS_AGENT_PROMPT,
    tools=[simple_crawl_tool],
)

filtering_agent = LlmAgent(
    name="filtering_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Constructs various url filters for crawler depending on the user instruction",
    instruction=FILTERING_AGENT_PROMPT,
    tools=[
        content_type_filter_tool,
        domain_filter_tool,
        url_filter_tool,
    ],
)

extraction_agent = LlmAgent(
    name="extraction_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Agent to perform web crawling and structured data extraction using various strategies",
    instruction=EXTRACTION_AGENT_PROMPT,
    tools=[
        perform_bfs_extraction_workflow,
        perform_dfs_extraction_workflow,
        perform_best_first_extraction_workflow,
    ],
)


sequential_agent = SequentialAgent(
    name="sequential_agent",
    sub_agents=[analysis_agent, filtering_agent, extraction_agent],
    description="Executes a sequence of page analysis, filter creation and crawling for data extraction",
)

# ? Implement coordinator-dispatcher with coordinator being the agent handling user request and dispatcher being the sequential agent?
# ? Looping agent for error handling until it completes?

#! Fix url pattern not setting correctly

# implement coordinator / dispatcher pattern
root_agent = Agent(
    name="coordinator_agent",
    model="gemini-2.5-pro-preview-05-06",
    description="Agent to coordinate execution by reasoning user instructions and delegating tasks to appropriate subagents.",
    instruction=COORDINATOR_AGENT_PROMPT,
    sub_agents=[sequential_agent],
)
