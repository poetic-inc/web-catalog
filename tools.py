import json
import os
from typing import List, Type

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from google import genai
from google.genai import types # Corrected import from google.type.types to google.genai.types
from pydantic import BaseModel

from filters import UniqueURLFilter # Updated import path
from prompt import EXTRACTION_PROMPT # Updated import path


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


async def format_data_md(extracted_content: str, extraction_prompt: str, extraction_schema: Type[BaseModel]):
    """
    Formats markdown content into structured JSON using a Gemini LLM.

    Args:
        extracted_content: The markdown content to format.
        extraction_prompt: The system instruction for the LLM.
        extraction_schema: The Pydantic model to enforce the output structure.

    Returns:
        A dictionary representing the extracted JSON data, or None if an error occurs.
    """
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model for formatting: {e}")
        return None

    try:
        res = await client.aio.models.generate_content(
            model="gemini-2.5-flash-preview-05-20",
            contents=f"Here is the input markdown: {extracted_content}",
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=extraction_schema,
                temperature=0.0,
                system_instruction=extraction_prompt,
            ),
        )
        json_data = json.loads(res.text)
        return json_data
    except Exception as e:
        print(f"Error calling Gemini API or processing response during formatting: {e}")
        return None


async def crawl_pages(
    start_url: str,
    page_patterns: List[str],
    max_pages: int = 15,
    max_depth: int = 15,
):
    """
    Performs web crawling and returns raw scraped page results.

    Args:
        start_url: The initial URL to start crawling from.
        page_patterns: A list of regex patterns for URLs that should be scraped.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum crawl depth.

    Returns:
        A list of ScrapedPage objects from crawl4ai.
    """
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
            f"Crawler finished. Found {len(results)} scraped page(s)."
        )
        return results # Returns list of ScrapedPage objects


async def perform_full_extraction_workflow(
    start_url: str,
    page_patterns: List[str],
    extraction_prompt: str,
    extraction_schema_name: str, # Agent will provide schema name as string
    max_pages: int = 15,
    max_depth: int = 15,
) -> List[dict]:
    """
    Performs a full web crawling and data extraction workflow.
    This tool orchestrates crawling pages and then extracting structured data from them.

    Args:
        start_url: The initial URL to start crawling from.
        page_patterns: A list of regex patterns for URLs that should be scraped.
        extraction_prompt: The system instruction for the data extraction LLM.
        extraction_schema_name: The name of the Pydantic model to use for structured extraction (e.g., "ResponseModel").
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum crawl depth.

    Returns:
        A list of dictionaries, where each dictionary is the extracted data from a page.
    """
    schema_map = {
        "ResponseModel": ResponseModel,
        # Add other potential schemas here if needed
    }
    extraction_schema_class = schema_map.get(extraction_schema_name)
    if not extraction_schema_class:
        print(f"Error: Unknown extraction schema name: {extraction_schema_name}")
        return []

    all_extracted_data: List[dict] = []

    scraped_pages = await crawl_pages(start_url, page_patterns, max_pages, max_depth)

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) with Gemini for extraction...")
    for res in scraped_pages:
        scraped_content = res.markdown
        current_url = res.url

        if scraped_content:
            print(f"Sending content from {current_url} to Gemini for formatting...")
            json_data = await format_data_md(scraped_content, extraction_prompt, extraction_schema_class)
            if json_data:
                all_extracted_data.append(json_data)
        else:
            print(f"No HTML content extracted from {current_url}. Skipping LLM processing.")

    return all_extracted_data
