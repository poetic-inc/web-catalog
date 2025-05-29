from typing import List, Optional


async def url_filter_tool(patterns: str):
    """
    Creates a URLPatternFilter instance from crawl4ai.

    This tool constructs a filter that allows crawling based on URL patterns.
    It's designed to be used by an LLM or a higher-level agent to specify
    which URLs should be included or excluded during a crawl based on
    wildcard or regex patterns.

    Args:
        patterns (str): A string containing wildcard or regex patterns.
                        URLs matching any of these patterns will be processed
                        by the crawler if this filter is applied.
                        Example: ".*example.com/products/.*,.*category/items/.*"

    Returns:
        dict: A dictionary describing the URL pattern filter,
              e.g., {"type": "url_pattern", "patterns": ".*example.com/products/.*"}
    """
    return {"type": "url_pattern", "patterns": patterns}


async def domain_filter_tool(allowed: List[str], blocked: List[str]):
    """
    Creates a DomainFilter instance from crawl4ai.

    This tool constructs a filter that allows or blocks crawling based on domain names.
    It's useful for restricting the crawl to specific domains or preventing
    the crawler from accessing certain domains.

    Args:
        allowed (List[str]): A list of domain names (e.g., "example.com")
                             from which URLs are allowed. If empty, all domains
                             not explicitly blocked are implicitly allowed (depending
                             on other filters).
        blocked (List[str]): A list of domain names from which URLs are
                             blocked. URLs from these domains will not be crawled.

    Returns:
        dict: A dictionary describing the domain filter,
              e.g., {"type": "domain", "allowed_domains": ["example.com"], "blocked_domains": ["ads.example.com"]}
    """
    return {"type": "domain", "allowed_domains": allowed, "blocked_domains": blocked}


async def content_type_filter_tool(allowed: List[str]):
    """
    Creates a ContentTypeFilter instance from crawl4ai.

    This tool constructs a filter that allows crawling based on the MIME content type
    of the web resources. It helps in focusing the crawl on specific types of
    content, such as HTML pages or PDF documents.

    Args:
        allowed (List[str]): A list of allowed MIME types (e.g.,
                             "text/html", "application/json"). Only URLs whose
                             content type matches one of these will be processed.

    Returns:
        dict: A dictionary describing the content type filter,
              e.g., {"type": "content_type", "allowed_types": ["text/html"]}
    """
    return {"type": "content_type", "allowed_types": allowed}
