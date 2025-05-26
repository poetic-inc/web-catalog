import json
import os
from typing import List, Type

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import (
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
    BestFirstCrawlingStrategy,
)
from crawl4ai.deep_crawling.filters import (
    FilterChain,
    URLPatternFilter,
    DomainFilter,
    ContentTypeFilter,
    ContentRelevanceFilter,
    SEOFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from google import genai
from google.genai import types
from pydantic import BaseModel

from filters import UniqueURLFilter
from prompt import EXTRACTION_PROMPT

from .models import ProductModel


async def _format_data_md(
    extracted_content: str, extraction_prompt: str, extraction_schema: Type[BaseModel]
):
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


async def _internal_crawl_pages(
    start_url: str,
    page_patterns: List[str],
    strategy_type: str,
    max_pages: int = 15,
    max_depth: int = 15,
    keywords: List[str] = None,
    # New filter parameters
    domain_filter_allowed: List[str] = None,
    domain_filter_blocked: List[str] = None,
    content_type_filter_allowed: List[str] = None,
    content_relevance_filter_query: str = None,
    content_relevance_filter_threshold: float = 0.7,
    seo_filter_keywords: List[str] = None,
    seo_filter_threshold: float = 0.5,
):
    """
    Internal helper to perform web crawling with a specified strategy and filters.
    """
    active_filters = [UniqueURLFilter()]
    active_filters.extend([URLPatternFilter(patterns=[p]) for p in page_patterns])

    if domain_filter_allowed or domain_filter_blocked:
        active_filters.append(
            DomainFilter(
                allowed_domains=domain_filter_allowed,
                blocked_domains=domain_filter_blocked,
            )
        )
    if content_type_filter_allowed:
        active_filters.append(
            ContentTypeFilter(allowed_types=content_type_filter_allowed)
        )
    if content_relevance_filter_query:
        active_filters.append(
            ContentRelevanceFilter(
                query=content_relevance_filter_query,
                threshold=content_relevance_filter_threshold,
            )
        )
    if seo_filter_keywords:
        active_filters.append(
            SEOFilter(keywords=seo_filter_keywords, threshold=seo_filter_threshold)
        )

    filter_chain = FilterChain(filters=active_filters)

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
            print("Warning: BestFirstCrawlingStrategy called without keywords. Scorer will be basic.")
            # Default to a null scorer or handle as an error if keywords are mandatory
            # For now, let's proceed, but it might not be effective.
            # A more robust solution might involve a default scorer or raising an error.
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
        scraping_strategy=LXMLWebScrapingStrategy(), # Added based on crawl4ai docs
        verbose=True,
    )

    browser_config = BrowserConfig(headless=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(
            f"Starting {strategy_type} deep scrape from {start_url} with patterns: {page_patterns}"
        )
        results = await crawler.arun(start_url, config=crawl_config)

        if not results:
            print(f"Crawler returned no results for {start_url}. No data to process.")
            return []

        print(f"Crawler finished. Found {len(results)} scraped page(s).")
        return results


async def perform_bfs_extraction_workflow(
    start_url: str,
    page_patterns: List[str],
    max_pages: int = 15,
    max_depth: int = 15,
    domain_filter_allowed: List[str] = None,
    domain_filter_blocked: List[str] = None,
    content_type_filter_allowed: List[str] = None,
    content_relevance_filter_query: str = None,
    content_relevance_filter_threshold: float = 0.7,
    seo_filter_keywords: List[str] = None,
    seo_filter_threshold: float = 0.5,
) -> List[dict]:
    """
    Performs BFS crawling and extracts data using ProductModel.
    Supports various optional filters.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
        strategy_type="BFS",
        max_pages=max_pages,
        max_depth=max_depth,
        domain_filter_allowed=domain_filter_allowed,
        domain_filter_blocked=domain_filter_blocked,
        content_type_filter_allowed=content_type_filter_allowed,
        content_relevance_filter_query=content_relevance_filter_query,
        content_relevance_filter_threshold=content_relevance_filter_threshold,
        seo_filter_keywords=seo_filter_keywords,
        seo_filter_threshold=seo_filter_threshold,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, EXTRACTION_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data


async def perform_dfs_extraction_workflow(
    start_url: str,
    page_patterns: List[str],
    max_pages: int = 15,
    max_depth: int = 15,
    domain_filter_allowed: List[str] = None,
    domain_filter_blocked: List[str] = None,
    content_type_filter_allowed: List[str] = None,
    content_relevance_filter_query: str = None,
    content_relevance_filter_threshold: float = 0.7,
    seo_filter_keywords: List[str] = None,
    seo_filter_threshold: float = 0.5,
) -> List[dict]:
    """
    Performs DFS crawling and extracts data using ProductModel.
    Supports various optional filters.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
        strategy_type="DFS",
        max_pages=max_pages,
        max_depth=max_depth,
        domain_filter_allowed=domain_filter_allowed,
        domain_filter_blocked=domain_filter_blocked,
        content_type_filter_allowed=content_type_filter_allowed,
        content_relevance_filter_query=content_relevance_filter_query,
        content_relevance_filter_threshold=content_relevance_filter_threshold,
        seo_filter_keywords=seo_filter_keywords,
        seo_filter_threshold=seo_filter_threshold,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, EXTRACTION_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data


async def perform_best_first_extraction_workflow(
    start_url: str,
    page_patterns: List[str],
    keywords: List[str],
    max_pages: int = 15,
    max_depth: int = 15,
    domain_filter_allowed: List[str] = None,
    domain_filter_blocked: List[str] = None,
    content_type_filter_allowed: List[str] = None,
    content_relevance_filter_query: str = None,
    content_relevance_filter_threshold: float = 0.7,
    seo_filter_keywords: List[str] = None,
    seo_filter_threshold: float = 0.5,
) -> List[dict]:
    """
    Performs BestFirst crawling using keywords and extracts data using ProductModel.
    Supports various optional filters.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
        strategy_type="BestFirst",
        max_pages=max_pages,
        max_depth=max_depth,
        keywords=keywords,
        domain_filter_allowed=domain_filter_allowed,
        domain_filter_blocked=domain_filter_blocked,
        content_type_filter_allowed=content_type_filter_allowed,
        content_relevance_filter_query=content_relevance_filter_query,
        content_relevance_filter_threshold=content_relevance_filter_threshold,
        seo_filter_keywords=seo_filter_keywords,
        seo_filter_threshold=seo_filter_threshold,
    )

    if not scraped_pages:
        return []

    print(f"Processing {len(scraped_pages)} scraped page(s) for extraction...")
    for res in scraped_pages:
        if res.markdown:
            json_data = await _format_data_md(
                res.markdown, EXTRACTION_PROMPT, ProductModel
            )
            if json_data:
                all_extracted_data.append(json_data)
    return all_extracted_data
