import asyncio
import json
import os
import re
from typing import List

from crawl4ai import AsyncWebCrawler, BrowserConfig, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy, DFSDeepCrawlStrategy
from crawl4ai.deep_crawling.filters import FilterChain, URLPatternFilter
from google import genai
from google.genai import types
from pydantic import BaseModel

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
    # pagination: str


async def use_llm_free(base_url: str):
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model: {e}")
        return

    all_extracted_data: List[ResponseModel] = []

    # url_pattern = r".*"  # Temporarily allow all internal links for testing
    # url_filter = URLPatternFilter(patterns=[url_pattern])
    # filter_chain = FilterChain(filters=[url_filter])  # Commented out for testing

    crawl_strategy = DFSDeepCrawlStrategy(
        max_depth=15,
        max_pages=15,
        include_external=False,
        # filter_chain=filter_chain, # Removed for testing
    )

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=crawl_strategy,
        verbose=True,
    )

    browser_config = BrowserConfig(headless=True, verbose=True)

    async with AsyncWebCrawler(config=browser_config) as crawler:
        print(f"Starting deep scrape from {base_url}")
        # Revert: Pass base_url as a string, not a list, to avoid TypeError
        results = await crawler.arun(base_url, config=crawl_config)
        print(results)

        if not results:
            print(f"Crawler returned no results for {base_url}. No data to process.")
            return

        print(
            f"Crawler finished. Processing {len(results)} scraped page(s) with Gemini..."
        )

        for res in results:
            scraped_content = res.markdown
            print(scraped_content)
            current_url = res.url
            # print(res.links) # Keep this commented out unless you need to see the links again

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

    print("\n--- Extraction Complete ---")
    if all_extracted_data:
        print(f"Successfully extracted data from {len(all_extracted_data)} page(s).")

        # Write data to JSON file
        data_dir = "data"
        os.makedirs(data_dir, exist_ok=True)
        file_path = os.path.join(data_dir, "extracted_data.json")
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                data_to_write = [item for item in all_extracted_data]
                json.dump(data_to_write, f, indent=4)
            print(f"Successfully wrote extracted data to {file_path}")
        except IOError as e:
            print(f"Error writing data to {file_path}: {e}")
    else:
        print("No data was extracted from any page.")


async def simple_crawl(base_url: str):
    async with AsyncWebCrawler() as crawler:
        res = await crawler.arun(base_url)
        print(res.markdown)


if __name__ == "__main__":
    asyncio.run(use_llm_free(base_url="https://bronsonshop.com/collections/clothing"))
    # asyncio.run(simple_crawl(base_url="https://bronsonshop.com/collections/clothing"))
