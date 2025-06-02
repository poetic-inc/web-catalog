from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent, LlmAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from src.prompt import (
    ANALYSIS_AGENT_PROMPT,
    COORDINATOR_AGENT_PROMPT,
    EXTRACTION_AGENT_PROMPT,
    FILTERING_AGENT_PROMPT,
    PLANNER_AGENT_PROMPT,
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

planner_agent = LlmAgent(
    name="planner_agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Generates a strategic crawling plan based on aggregated page analysis.",
    instruction=PLANNER_AGENT_PROMPT,
    tools=[],
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


# implement coordinator / dispatcher pattern
coordinator_agent = Agent(
    name="coordinator_agent_logic",
    model="gemini-2.5-pro-preview-05-06",
    description="Agent to coordinate execution by reasoning user instructions and delegating tasks to appropriate subagents. It updates 'overall_status' in session state to 'in_progress' or 'completed'.",
    instruction=COORDINATOR_AGENT_PROMPT
    + "\n\nWhen you believe the user's overall request is fully satisfied, ensure you update the session state by setting a field 'overall_status' to 'completed'. Otherwise, set it to 'in_progress' or reflect the current stage.",
    sub_agents=[
        analysis_agent,
        planner_agent,
        filtering_agent,
        extraction_agent,
    ],
)


class ConditionCheckAgent(BaseAgent):
    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        print("Checking the state of the current user request... ")
        overall_status = ctx.session.state.get("overall_status", "in_progress")
        is_done = overall_status == "completed"
        yield Event(
            author=self.name,
            actions=EventActions(escalate=is_done),
        )


iterative_coordinator = LoopAgent(
    name="IterativeCoordinator",
    sub_agents=[
        coordinator_agent,
        ConditionCheckAgent(name="OverallCompletionChecker"),
    ],
    description="Coordinates multi-step tasks by iteratively running a logic agent and a completion checker.",
)


root_agent = iterative_coordinator
