import json
import os
from typing import List, Optional, Type

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.content_scraping_strategy import LXMLWebScrapingStrategy
from crawl4ai.deep_crawling import (
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
)
from crawl4ai.deep_crawling.filters import (
    ContentRelevanceFilter,
    ContentTypeFilter,
    DomainFilter,
    FilterChain,
    SEOFilter,
    URLPatternFilter,
)
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from google import genai
from google.genai import types
from pydantic import BaseModel

from filters import UniqueURLFilter
from models import ProductModel
from prompt import FORMATTING_PROMPT


async def _format_data_md(
    extracted_content: str, formatting_prompt: str, extraction_schema: Type[BaseModel]
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


async def _internal_crawl_pages(
    start_url: str,
    strategy_type: str,
    page_patterns: List[str] = None,
    max_pages: int = None,
    max_depth: int = None,
    keywords: List[str] = None,
):
    """
    Internal helper to perform web crawling with a specified strategy and filters.
    """
    # TODO: implement different filter strategies
    filter_chain = FilterChain(
        [
            UniqueURLFilter(),
            URLPatternFilter(patterns=page_patterns),
        ]
    )

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
        scraping_strategy=LXMLWebScrapingStrategy(),  # Added based on crawl4ai docs
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
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Breadth-First Search (BFS) web crawl starting from a given URL and extracts structured data from pages matching specified patterns.

    This tool crawls web pages using a BFS strategy, meaning it explores all pages at the current depth level before moving to the next. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        page_patterns: A list of string patterns. Only URLs matching these patterns will be scraped. Supports both wildcard syntax and regex for more complex pattern.
        filter_type: filters to select urls to crawl. Five modes available: url, domain, content-type, content-relevance and seo.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
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
    page_patterns: List[str],
    max_pages: int = 15,
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Depth-First Search (DFS) web crawl starting from a given URL and extracts structured data from pages matching specified patterns.

    This tool crawls web pages using a DFS strategy, meaning it explores as far as possible along each branch before backtracking. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        page_patterns: A list of string patterns. Only URLs matching these patterns will be scraped. Supports both wildcard syntax and regex for more complex pattern.
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
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
    page_patterns: List[str],
    keywords: List[str],
    max_pages: int = 15,
    max_depth: int = 3,
) -> List[dict]:
    """Performs a Best-First Search web crawl using keywords to score and prioritize URLs, then extracts structured data from pages matching specified patterns.

    This tool crawls web pages by prioritizing URLs that are most relevant to the provided keywords. It filters pages based on URL patterns and extracts information according to the ProductModel schema.

    Args:
        start_url: The initial URL to begin crawling from.
        page_patterns: A list of string patterns. Only URLs matching these patterns will be scraped. Supports both wildcard syntax and regex for more complex pattern.
        keywords: A list of keywords used to score and prioritize URLs for crawling. For example, ["camera", "review", "price"].
        max_pages: The maximum number of pages to crawl.
        max_depth: The maximum depth to crawl from the start_url.

    Returns:
        A list of dictionaries, where each dictionary represents structured data extracted from a scraped page, conforming to the ProductModel. Returns an empty list if no data is extracted or no pages are found.
    """
    all_extracted_data: List[dict] = []
    scraped_pages = await _internal_crawl_pages(
        start_url=start_url,
        page_patterns=page_patterns,
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


async def simple_crawl_tool(start_url: str) -> str:
    """Fetches the main content of a single web page and returns it as markdown.

    This tool is designed to perform a quick scrape of a given URL to retrieve its primary textual content.
    The output is intended for initial analysis by an LLM to understand the page's content, structure,
    and potential areas of interest before deciding on more complex crawling or data extraction strategies.

    Args:
        start_url: The URL of the web page to crawl

    Returns:
        A string containing the markdown representation of the main content of the scraped web page.
        Returns an empty string if the page has no extractable markdown content or if the crawl fails
        to produce markdown.
    """
    async with AsyncWebCrawler() as crawler:
        print(f"Running ananlysis on the page: {start_url}...")
        result = await crawler.arun(url=start_url)

    return result.markdown if result and result.markdown else ""


async def filter_generation_tool(
    url_filter_args: Optional[dict] = None,
    domain_filter_args: Optional[dict] = None,
    content_type_filter_args: Optional[dict] = None,
):
    """
    Constructs a list of crawl4ai filter instances based on provided arguments.

    This tool is designed to be called by an LLM or a higher-level agent
    to dynamically create filters for web crawling tasks based on user
    instructions or inferred requirements. Each argument corresponds to a
    specific type of filter from the crawl4ai library. The created filters
    can then be used in a crawl4ai FilterChain.

    Args:
        url_filter_args (Optional[dict]): Arguments for creating a
            `crawl4ai.deep_crawling.filters.URLPatternFilter`.
            If provided, it should be a dictionary with the following key:
            - "patterns" (List[str]): A list of regex patterns. URLs matching
              any of these patterns will be processed by the crawler if this
              filter is applied.
              Example: `{"patterns": [".*example.com/products/.*", ".*category/items/.*"]}`

        domain_filter_args (Optional[dict]): Arguments for creating a
            `crawl4ai.deep_crawling.filters.DomainFilter`.
            If provided, it should be a dictionary with one or both of the
            following keys:
            - "allowed" (List[str]): A list of domain names (e.g., "example.com")
              from which URLs are allowed.
            - "blocked" (List[str]): A list of domain names from which URLs are
              blocked.
            Example: `{"allowed": ["example.com", "another.org"], "blocked": ["ads.example.com"]}`

        content_type_filter_args (Optional[dict]): Arguments for creating a
            `crawl4ai.deep_crawling.filters.ContentTypeFilter`.
            If provided, it should be a dictionary with the following key:
            - "allowed" (List[str]): A list of allowed MIME types (e.g.,
              "text/html", "application/json"). Only URLs whose content type
              matches one of these will be processed.
            Note: The underlying `crawl4ai.deep_crawling.filters.ContentTypeFilter`
            also supports "blocked_types", but this tool currently only exposes
            the "allowed" types functionality.
            Example: `{"allowed": ["text/html", "application/pdf"]}`

    Returns:
        List[URLFilter]: A list containing the configured filter instances from
                         `crawl4ai.deep_crawling.filters`. This list can be
                         passed to a `crawl4ai.deep_crawling.filters.FilterChain`.
                         Returns an empty list if no arguments are provided or if
                         the provided arguments do not lead to the creation of any filters.

    Example of how an LLM might be instructed to use this tool:
    User instruction: "Crawl product pages on 'my-shop.com' but only look at HTML pages, and avoid the 'archive.my-shop.com' subdomain."

    LLM conceptual call:
    ```
    filter_generation_tool(
        url_filter_args={"patterns": [".*my-shop.com/product/.*"]},
        domain_filter_args={"allowed": ["my-shop.com"], "blocked": ["archive.my-shop.com"]},
        content_type_filter_args={"allowed": ["text/html"]}
    )
    ```
    This would conceptually return a list of filter objects like:
    `[URLPatternFilter_instance, DomainFilter_instance, ContentTypeFilter_instance]`
    where each instance is configured according to the arguments.
    """
    filters = []

    if url_filter_args:
        patterns = url_filter_args["patterns"]
        url_filter = URLPatternFilter(patterns=patterns)
        filters.extend(url_filter)

    if domain_filter_args:
        allowed = (domain_filter_args["allowed"],)
        blocked = (domain_filter_args["blocked"],)
        domain_filter = DomainFilter(
            allowed_domains=allowed,
            blocked_domains=blocked,
        )
        filters.extend(domain_filter)

    if content_type_filter_args:
        allowed = content_type_filter_args["allowed"]
        content_type_filter = ContentTypeFilter(allowed_types=allowed)
        filters.extend(content_type_filter)

    return filters
