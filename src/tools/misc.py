from crawl4ai import AsyncWebCrawler


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
