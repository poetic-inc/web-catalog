import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    CrawlerRunConfig,
    CacheMode,
)
from crawl4ai.extraction_strategy import LLMExtractionStrategy # Unused, but keeping for now as it might be used later
import json
import os
from google import genai, types
from pydantic import BaseModel
from typing import List
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DeepCrawlStrategy # DeepCrawlStrategy unused, but keeping for now
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer # Unused, but keeping for now
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter # Unused, but keeping for now

from prompt import PROMPT


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
    pages: List[Page]
    pagination: str


async def use_llm_free(base_url: str):
    try:in
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model: {e}")
        return

    page_number = 1
    all_extracted_data: List[ResponseModel] = []

    crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=0,
        max_pages=1,
        include_external=False,
    )

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=crawl_strategy,
        verbose=True,
    )

    async with AsyncWebCrawler() as crawler:
        pagination_logic = None

        while True:
            if page_number > 2:
                break

            if pagination_logic = "ui":
                # TODO: implement ui based logic
            else:
                # TODO: implement JS logic

            current_url = f"{base_url}?page={page_number}"

            print(f"Starting scrape for {current_url}")
            results = await crawler.arun(current_url, config=crawl_config)

            if not results:
                print(
                    f"Crawler returned no results for {current_url}. Assuming end of pagination or issue."
                )
                break

            res = results[0]
            scraped_content = res.html

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
                            response_schema=ResponseModel,
                            temperature=0.0,
                            system_instruction=PROMPT,
                        ),
                    )
                    json_output = response.text

                    all_extracted_data.append(json_output)
                    page_number += 1

                except Exception as e:
                    print(
                        f"Error calling Gemini API or processing response for {current_url}: {e}"
                    )
                    break
            else:
                print(
                    f"No markdown content extracted from {current_url}. Assuming end of pagination."
                )
                break

    print("\n--- Pagination Complete ---")
    if all_extracted_data:
        print(f"Successfully extracted data from {page_number -1} page(s).")
        print(all_extracted_data)
    else:
        print("No data was extracted from any page.")


async def simple_crawl(url: str):
    async with AsyncWebCrawler() as crawler:
        res = await crawler.arun(url)
        print(res.markdown)


if __name__ == "__main__":
    asyncio.run(use_llm_free(base_url="https://bronsonshop.com/collections/clothing"))
