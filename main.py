import asyncio
import json
import os
import re
from typing import List
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


async def use_llm_free(base_url: str):
    try:
        client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    except Exception as e:
        print(f"Error initializing Gemini client or model: {e}")
        return

    all_extracted_data: List[ResponseModel] = []

    url_pattern = r".*\?page=\d+"
    url_filter = URLPatternFilter(patterns=[url_pattern])
    filter_chain = FilterChain(filters=[UniqueURLFilter(), url_filter])

    crawl_strategy = BFSDeepCrawlStrategy(
        max_depth=15,
        max_pages=15,
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
        print(f"Starting deep scrape from {base_url}")
        results = await crawler.arun(base_url, config=crawl_config)

        if not results:
            print(f"Crawler returned no results for {base_url}. No data to process.")
            return

        print(
            f"Crawler finished. Processing {len(results)} scraped page(s) with Gemini..."
        )

        for res in results:
            scraped_content = res.markdown
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
