import asyncio
from crawl4ai import (
    AsyncWebCrawler,
    BrowserConfig,
    CrawlerRunConfig,
    CacheMode,
    LLMConfig,
)
from crawl4ai.extraction_strategy import LLMExtractionStrategy
import json
import os
from google import genai, types
from pydantic import BaseModel
from typing import List
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DeepCrawlStrategy
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter

from .prompt import PROMPT


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


async def use_llm_free(base_url: str):
    try:
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
        while True:
            if page_number > 2:
                break

            current_url = f"{base_url}?page={page_number}"

            print(f"Starting scrape for {current_url}")
            results = await crawler.arun(current_url, config=crawl_config)

            if not results:
                print(
                    f"Crawler returned no results for {current_url}. Assuming end of pagination or issue."
                )
                break

            # We expect one result because max_pages=1
            res = results[0]
            scraped_content = res.markdown

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
                    parsed_json_list = json.loads(json_output)
                    if not parsed_json_list:
                        print(
                            f"LLM returned no data for {current_url}. Assuming end of pagination."
                        )
                        break

                    all_extracted_data.append(parsed_json_list)
                    page_number += 1

                except Exception as e:
                    print(
                        f"Error calling Gemini API or processing response for {current_url}: {e}"
                    )
                    break
            else:
                print(
                    f"No markdown content extracted from {current_url} by Crawl4AI. Assuming end of pagination."
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
    # asyncio.run(simple_crawl(url="https://bronsonshop.com/collections/clothing?page=1"))
