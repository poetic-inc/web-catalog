import asyncio
import json
import os
from typing import List

from google import genai
from google.genai import types
from pydantic import BaseModel

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import BFSDeepCrawlStrategy

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
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model: {e}")
        return

    all_extracted_data: List[ResponseModel] = []

    crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=2,
        max_pages=10,
        include_external=False,
    )

    crawl_config = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        deep_crawl_strategy=crawl_strategy,
        verbose=True,
    )

    async with AsyncWebCrawler() as crawler:
        print(f"Starting deep scrape from {base_url}")
        results = await crawler.arun(base_url, config=crawl_config)

        if not results:
            print(f"Crawler returned no results for {base_url}. No data to process.")
            return

        print(f"Crawler finished. Processing {len(results)} scraped page(s) with Gemini...")

        for res in results:
            scraped_content = res.html
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
                    # Continue to the next page even if one fails
            else:
                print(
                    f"No HTML content extracted from {current_url}. Skipping LLM processing for this page."
                )

    print("\n--- Extraction Complete ---")
    if all_extracted_data:
        print(f"Successfully extracted data from {len(all_extracted_data)} page(s).")
        # For better readability, print each extracted item
        for data in all_extracted_data:
            print(f"Page URL: {data.page_url}")
            print(f"Page Name: {data.page_name}")
            print(f"Products: {len(data.products)} categories")
            print(f"Pages (internal links): {len(data.pages)}")
            print(f"Pagination Info: {data.pagination}")
            print("-" * 20)
    else:
        print("No data was extracted from any page.")


async def simple_crawl(base_url: str):
    async with AsyncWebCrawler() as crawler:
        res = await crawler.arun(base_url)
        print(res.markdown)


if __name__ == "__main__":
    # asyncio.run(use_llm_free(base_url="https://bronsonshop.com/collections/clothing"))
    asyncio.run(simple_crawl(base_url="https://bronsonshop.com/collections/clothing"))
