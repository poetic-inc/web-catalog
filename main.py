import asyncio
import json
import os
import re
from typing import List, Type  # Import Type for type hints
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CacheMode,
    CrawlerRunConfig,
    URLFilter,
)
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from google import genai
from google.genai import types
from pydantic import BaseModel

# PROMPT is no longer directly used by crawl_and_extract_data,
# but the agent might use it as a default or generate similar content.
# from prompt import PROMPT


class Item(BaseModel):
    name: str
    price: str
    url: str


class Product(BaseModel):
    category: str
    items: List[Item]


class Page(BaseModel):
    name: str
    url: str


class ResponseModel(BaseModel):
    page_url: str
    page_name: str
    products: List[Product]
    # pagination: str


class UniqueURLFilter(URLFilter):
    def __init__(self):
        super().__init__(name="UniqueURLFilter")
        self.seen_urls = set()

    def _normalize_url(self, url: str) -> str:
        """
        Normalizes a URL to a canonical form to help identify duplicates.
        Handles scheme, netloc, path, and query parameters.
        """
        parsed_url = urlparse(url)

        # Lowercase scheme and netloc for consistency
        scheme = parsed_url.scheme.lower()
        netloc = parsed_url.netloc.lower()

        # Remove 'www.' prefix from netloc if present
        if netloc.startswith("www."):
            netloc = netloc[4:]

        # Remove default ports from netloc
        if (scheme == "http" and netloc.endswith(":80")) or (
            scheme == "https" and netloc.endswith(":443")
        ):
            netloc = netloc.rsplit(":", 1)[0]  # Remove the last colon and port number

        # Remove fragment identifiers (e.g., #section) as they don't change the resource
        fragment = ""

        # Normalize path:
        # - Lowercase the path
        # - If the path is just '/', treat it as empty (e.g., example.com/ is same as example.com)
        # - Otherwise, remove trailing slashes
        normalized_path = parsed_url.path.lower()  # Lowercase path
        if normalized_path == "/":
            normalized_path = ""
        elif normalized_path.endswith("/"):
            normalized_path = normalized_path.rstrip("/")

        # Normalize query parameters: parse, sort by key, and re-encode
        # This ensures that order of parameters doesn't create a "new" URL
        query_params = parse_qs(parsed_url.query)
        sorted_query_items = []
        for key in sorted(query_params.keys()):
            # Ensure values for each key are also sorted and normalized (e.g., remove trailing slashes)
            for value in sorted(query_params[key]):
                normalized_value = value.rstrip(
                    "/"
                )  # Remove trailing slashes from query parameter values
                sorted_query_items.append((key, normalized_value))
        query = urlencode(sorted_query_items, doseq=True)

        # Reconstruct the URL from normalized components
        normalized_url = urlunparse(
            (scheme, netloc, normalized_path, parsed_url.params, query, fragment)
        )

        return normalized_url

    def apply(self, url: str) -> bool:
        normalized_url = self._normalize_url(url)
        if normalized_url in self.seen_urls:
            self._update_stats(False)
            return False
        else:
            self.seen_urls.add(normalized_url)
            self._update_stats(True)
            return True


# Refactored use_llm_free into a more generic tool
async def crawl_and_extract_data(
    start_url: str,
    page_patterns: List[str],
    extraction_prompt: str,
    extraction_schema: Type[BaseModel],  # Use Type for class hint
    max_pages: int = 15,
    max_depth: int = 15,
) -> List[dict]:
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model: {e}")
        return []

    all_extracted_data: List[dict] = []  # Changed to dict as json.loads returns dict

    # Dynamically create URLPatternFilters based on agent's plan
    url_pattern_filters = [URLPatternFilter(patterns=[p]) for p in page_patterns]
    filter_chain = FilterChain(filters=[UniqueURLFilter(), *url_pattern_filters])

    crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=max_depth,
        max_pages=max_pages,
        include_external=False,
        filter_chain=filter_chain,
    )

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=crawl_strategy,
        verbose=True,
    )

    browser_config = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Starting deep scrape from {start_url} with patterns: {page_patterns}")
        results = await crawler.arun(start_url, config=crawl_config)

        if not results:
            print(f"Crawler returned no results for {start_url}. No data to process.")
            return []

        print(
            f"Crawler finished. Processing {len(results)} scraped page(s) with Gemini..."
        )

        for res in results:
            scraped_content = res.markdown
            current_url = res.url

            if scraped_content:
                print(
                    f"Scraped content successfully from {current_url}. Sending to Gemini for formatting..."
                )
                try:
                    response = await client.aio.models.generate_content(
                        model="gemini-2.5-flash-preview-05-20",
                        contents=f"Here is the input markdown: {scraped_content}",
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=extraction_schema,  # Use the dynamic schema
                            temperature=0.0,
                            system_instruction=extraction_prompt,  # Use the dynamic prompt
                        ),
                    )
                    json_data = json.loads(response.text)
                    all_extracted_data.append(json_data)

                except Exception as e:
                    print(
                        f"Error calling Gemini API or processing response for {current_url}: {e}"
                    )
            else:
                print(
                    f"No HTML content extracted from {current_url}. Skipping LLM processing for this page."
                )
    return all_extracted_data


# New: Agent Orchestrator
class AgentPlan(BaseModel):
    action: str
    start_url: str
    page_patterns: List[str]
    extraction_prompt: str
    extraction_schema_name: str  # e.g., "ResponseModel"
    max_pages: int = 15
    max_depth: int = 15


async def run_agent(user_instruction: str):
    try:
        agent_llm_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client for agent: {e}")
        return

    # Map schema names to actual Pydantic classes
    schema_map = {
        "ResponseModel": ResponseModel,
        # Add other potential schemas here if needed
    }

    agent_prompt = f"""
    You are an intelligent web scraping agent. Your goal is to understand user instructions and generate a plan to scrape and extract relevant data.

    Based on the following user instruction, generate a JSON plan.
    The JSON plan must strictly adhere to the following structure:
    - "action": (string) Must be "crawl_and_extract". This is the only supported action for now.
    - "start_url": (string) The initial URL to start crawling from.
    - "page_patterns": (list of strings) A list of regex patterns for URLs that should be scraped. Use `.*` for any character. For example, if the user wants product pages, you might use `["https://example.com/products/.*"]`. If they want paginated category pages, `["https://example.com/category.*page=\\d+"]`.
    - "extraction_prompt": (string) The system instruction for the data extraction LLM. This prompt should guide the LLM on what data to extract and how to format it, based on the user's request.
    - "extraction_schema_name": (string) The name of the Pydantic model to use for structured extraction (e.g., "ResponseModel").
    - "max_pages": (integer) The maximum number of pages to crawl.
    - "max_depth": (integer) The maximum crawl depth.

    The available Pydantic schemas for the "extraction_schema_name" field are:
    - "ResponseModel": This schema expects the following structure:
        - page_url (string): The URL of the page.
        - page_name (string): The name or title of the page.
        - products (list of Product objects): A list of product details found on the page.
            - Each Product object has:
                - category (string): The category of the product.
                - items (list of Item objects): A list of individual items within that product category.
                    - Each Item object has:
                        - name (string): The name of the item.
                        - price (string): The price of the item.
                        - url (string): The URL of the item.

    User Instruction: "{user_instruction}"

    Example for "Find all clothing items and their prices from bronsonshop.com/collections/clothing":
    ```json
    {{
        "action": "crawl_and_extract",
        "start_url": "https://bronsonshop.com/collections/clothing",
        "page_patterns": [".*bronsonshop.com/collections/clothing.*page=\\d+"],
        "extraction_prompt": "Extract the category, name, price, and URL for all clothing items on the page. Ensure the output strictly adheres to the ResponseModel schema.",
        "extraction_schema_name": "ResponseModel",
        "max_pages": 15,
        "max_depth": 15
    }}
    ```
    Your JSON plan:
    """

    print(f"Agent received instruction: '{user_instruction}'")
    try:
        agent_response = await agent_llm_client.aio.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",  # Or gemini-pro for more complex reasoning
            contents=agent_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                # response_schema=AgentPlan,  # Removed as per request
                temperature=0.0,
            ),
        )
        plan_data = json.loads(agent_response.text)
        plan = AgentPlan(**plan_data)

        if plan.action == "crawl_and_extract":
            extraction_schema_class = schema_map.get(plan.extraction_schema_name)
            if not extraction_schema_class:
                print(
                    f"Error: Unknown extraction schema name: {plan.extraction_schema_name}"
                )
                return

            print(f"Agent decided to execute plan: {plan.model_dump_json(indent=2)}")
            extracted_data = await crawl_and_extract_data(
                start_url=plan.start_url,
                page_patterns=plan.page_patterns,
                extraction_prompt=plan.extraction_prompt,
                extraction_schema=extraction_schema_class,
                max_pages=plan.max_pages,
                max_depth=plan.max_depth,
            )
            print("\n--- Agent Workflow Complete ---")
            if extracted_data:
                print(
                    f"Agent successfully extracted data from {len(extracted_data)} page(s)."
                )

                # Write data to JSON file
                data_dir = "data"
                os.makedirs(data_dir, exist_ok=True)
                file_path = os.path.join(data_dir, "agent_extracted_data.json")
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(extracted_data, f, indent=4)
                    print(f"Successfully wrote agent extracted data to {file_path}")
                except IOError as e:
                    print(f"Error writing data to {file_path}: {e}")
            else:
                print("Agent extracted no data.")
        else:
            print(f"Agent generated an unsupported action: {plan.action}")

    except Exception as e:
        print(f"Error in agent orchestration: {e}")
        print(
            f"Agent response text (if available): {getattr(agent_response, 'text', 'N/A')}"
        )


async def simple_crawl(base_url: str):
    async with AsyncWebCrawler() as crawler:
        res = await crawler.arun(base_url)
        print(res.markdown)


if __name__ == "__main__":
    # Example usage of the agent
    asyncio.run(
        run_agent(
            user_instruction="Find all clothing items and their prices from bronsonshop.com/collections/clothing"
        )
    )
    # asyncio.run(simple_crawl(base_url="https://bronsonshop.com/collections/clothing"))
