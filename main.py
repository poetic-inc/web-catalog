import asyncio
import json
import os
# Removed unused imports: re, Type, List, BaseModel, UniqueURLFilter,
# AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig,
# BFSDeepCrawlStrategy, FilterChain, URLPatternFilter, genai, types

# Import the ADK agent
from agent.agent import root as adk_agent


async def run_agent(user_instruction: str):
    """
    Runs the ADK agent with a given user instruction and processes its output.
    """
    print(f"Agent received instruction: '{user_instruction}'")
    try:
        # The ADK agent will decide which tool to call based on its instruction and the user_instruction.
        # The result will be streamed back.
        response_stream = adk_agent.stream_content(user_instruction)

        all_extracted_data = []
        async for chunk in response_stream:
            if chunk.text:
                print(f"Agent says: {chunk.text}")
            if chunk.tool_code:
                print(f"Agent executed tool: {chunk.tool_code.tool_name} with args: {chunk.tool_code.args}")
            if chunk.tool_response:
                # This is where the result from perform_full_extraction_workflow will come back
                tool_output = chunk.tool_response.output
                if tool_output:
                    print(f"Tool response received. Type: {type(tool_output)}")
                    # Assuming the tool returns a list of dicts (the extracted data)
                    if isinstance(tool_output, list):
                        all_extracted_data.extend(tool_output)
                    else:
                        print(f"Unexpected tool output type: {type(tool_output)}. Expected list.")
                        # For now, just print it if it's not a list
                        print(tool_output)

        print("\n--- Agent Workflow Complete ---")
        if all_extracted_data:
            print(f"Agent successfully extracted data from {len(all_extracted_data)} page(s).")

            # Write data to JSON file
            data_dir = "data"
            os.makedirs(data_dir, exist_ok=True)
            file_path = os.path.join(data_dir, "agent_extracted_data.json")
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(all_extracted_data, f, indent=4)
                print(f"Successfully wrote agent extracted data to {file_path}")
            except IOError as e:
                print(f"Error writing data to {file_path}: {e}")
        else:
            print("Agent extracted no data.")

    except Exception as e:
        print(f"Error in agent orchestration: {e}")


# simple_crawl is not part of the agentic workflow and is removed for clarity.
# If needed, it can be re-added with its necessary imports.


if __name__ == "__main__":
    # Example usage of the agent
    asyncio.run(
        run_agent(
            user_instruction="Find all clothing items and their prices from bronsonshop.com/collections/clothing"
        )
    )
