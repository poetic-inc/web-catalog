import json
import os
from typing import List, Optional, Type

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import (
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
)
from crawl4ai.deep_crawling.filters import (
    ContentTypeFilter,
    DomainFilter,
    FilterChain,
    URLPatternFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from google import genai
from google.genai import types
from pydantic import BaseModel

from ..models import ProductModel
from ..prompt import FORMATTING_PROMPT


async def _crawl_pages(
    start_url: str,
    strategy_type: str,
    filters: List[dict] = None,
    max_pages: int = None,
    max_depth: int = None,
    keywords: List[str] = None,
):
    """
    Internal helper to perform web crawling with a specified strategy and filters.
    """
    if filters:
        filter_objs = []
        for f in filters:
            if f["type"] == "url_pattern":
                filter_objs.append(URLPatternFilter(patterns=f["patterns"]))
            elif f["type"] == "domain":
                filter_objs.append(
                    DomainFilter(
                        allowed_domains=f["allowed_domains"],
                        blocked_domains=f["blocked_domains"],
                    )
                )
            elif f["type"] == "content_type":
                filter_objs.append(ContentTypeFilter(allowed_types=f["allowed_types"]))
            else:
                continue

        filter_chain = FilterChain(filter_objs)
    else:
        filter_chain = None

    if strategy_type == "BFS":
        crawl_strategy = BFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
        )
    elif strategy_type == "DFS":
        crawl_strategy = DFSDeepCrawlStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
        )
    elif strategy_type == "BestFirst":
        if not keywords:
            print(
                "Warning: BestFirstCrawlingStrategy called without keywords. Scorer will be basic."
            )
            url_scorer = None
        else:
            url_scorer = KeywordRelevanceScorer(keywords=keywords, weight=0.7)

        crawl_strategy = BestFirstCrawlingStrategy(
            max_depth=max_depth,
            max_pages=max_pages,
            include_external=False,
            filter_chain=filter_chain,
            url_scorer=url_scorer,
        )
    else:
        raise ValueError(f"Unsupported crawl strategy type: {strategy_type}")

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=crawl_strategy,
        verbose=True,
    )

    browser_config = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Starting {strategy_type} deep scrape from {start_url}")
        results = await crawler.arun(start_url, config=crawl_config)

        if not results:
            print(f"Crawler returned no results for {start_url}. No data to process.")
            return []

        print(f"Crawler finished. Found {len(results)} scraped page(s).")
        return results


async def _format_data_md(
    extracted_content: str,
    formatting_prompt: str,
    extraction_schema: Type[BaseModel],
):
    """
    Formats markdown content into structured JSON using a Gemini LLM.

    Args:
        extracted_content: The markdown content to format.
        formatting_prompt: The system instruction for the LLM.
        extraction_schema: The Pydantic model to enforce the output structure.

    Returns:
        A dictionary representing the extracted JSON data, or None if an error occurs.
    """
    try:
        client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
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
                system_instruction=formatting_prompt,
            ),
        )
        json_data = json.loads(res.text)
        return json_data
    except Exception as e:
        print(f"Error calling Gemini API or processing response during formatting: {e}")
        return None


async def perform_bfs_extraction_workflow(
    start_url: str,
    filters: Optional[List[dict]] = None,
    max_pages: int = 15,
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Breadth-First Search (BFS) web crawl starting from a given URL and extracts structured data from pages matching specified patterns.

    This tool crawls web pages using a BFS strategy, meaning it explores all pages at the current depth level before moving to the next. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        filters: A list of filter configuration used to construct filter objects for crawling.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _crawl_pages(
        start_url=start_url,
        filters=filters,
        strategy_type="BFS",
        max_pages=max_pages,
        max_depth=max_depth,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, FORMATTING_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data


async def perform_dfs_extraction_workflow(
    start_url: str,
    filters: Optional[List[dict]] = None,
    max_pages: int = 15,
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Depth-First Search (DFS) web crawl starting from a given URL and extracts structured data from pages matching specified patterns.

    This tool crawls web pages using a DFS strategy, meaning it explores as far as possible along each branch before backtracking. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        filters: A list of filter configuration used to construct filter objects for crawling.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _crawl_pages(
        start_url=start_url,
        filters=filters,
        strategy_type="DFS",
        max_pages=max_pages,
        max_depth=max_depth,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, FORMATTING_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data


async def perform_best_first_extraction_workflow(
    start_url: str,
    keywords: List[str],
    filters: Optional[List[dict]] = None,
    max_pages: int = 15,
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Best-First Search web crawl using keywords to score and prioritize URLs, then extracts structured data from pages matching specified patterns.

    This tool crawls web pages by prioritizing URLs that are most relevant to the provided keywords. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        keywords: A list of keywords used to score and prioritize URLs for crawling. For example, ["camera", "review", "price"].
        filters: A list of filter configuration used to construct filter objects for crawling.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _crawl_pages(
        start_url=start_url,
        filters=filters,
        strategy_type="BestFirst",
        max_pages=max_pages,
        max_depth=max_depth,
        keywords=keywords,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, FORMATTING_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data
