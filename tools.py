import json
import os
from typing import List

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from google import genai
from google.type import types
from pydantic import BaseModel

from .filters import UniqueURLFilter
from .prompt import EXTRACTION_PROMPT


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


async def format_data_md(extracted_content: str):
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

    res = await client.aio.models.generate_content(
        model="gemini-2.5-flash-preview-05-20",
        contents=f"Here is the input markdown: {extracted_content}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ResponseModel,
            temperature=0.0,
            system_instruction=EXTRACTION_PROMPT,
        ),
    )

    json_data = json.loads(res.text)

    return json_data


async def crawl_and_extract_data(
    start_url: str,
    page_patterns: List[str],
    max_pages: int = 15,
    max_depth: int = 15,
) -> List[dict]:

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

        return results
