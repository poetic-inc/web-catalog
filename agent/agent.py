from google.adk.agents import Agent

from ..prompt import AGENT_PROMPT
from ..tools import crawl_and_extract_data, format_data_md

root = Agent(
    name="test-agent",
    model="gemini-2.5-flash-preview-05-20",
    description="Agent to perform web crawling",
    instruction=AGENT_PROMPT,
    tools=[crawl_and_extract_data, format_data_md],
)
