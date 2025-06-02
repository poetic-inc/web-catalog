from typing import List, Optional


async def url_filter_tool(patterns: List[str]):
    """
    This tool constructs a filter that allows crawling based on URL patterns.
    It's designed to be used by an LLM or a higher-level agent to specify
    which URLs should be included or excluded during a crawl based on
    wildcard or regex patterns.

    Args:
        patterns (List[str]): A list of string to match using wildcard syntax or regex pattern.
                        URLs matching any of these patterns will be processed
                        by the crawler if this filter is applied.
                        To use regex pattern, the pattern should resort true from at least one of the following condition:
                            - start with `^`
                            - end with `$`
                            - contains `\d`
                        Example: to match url with `shop`, you would do: *example.com/shop* (wildcard) or ^.*example\.com/shop.* (regex)

    Returns:
        dict: A dictionary representing the configuration for a URL pattern filter.
              This dictionary includes the filter type ("url_pattern") and the
              patterns string.
              Example: `{"type": "url_pattern", "patterns": "*example.com/products/*"}`
    """
    print(f"Constructing URL filter for crawler...")
    return {"type": "url_pattern", "patterns": patterns}


async def domain_filter_tool(allowed: List[str], blocked: List[str]):
    """
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
        dict: A dictionary representing the configuration for a domain filter.
              This dictionary includes the filter type ("domain"), a list of
              allowed domains, and a list of blocked domains.
              Example: `{"type": "domain", "allowed_domains": ["example.com"], "blocked_domains": ["ads.example.com"]}`
    """
    print(f"Constructing domain filter for crawler...")
    return {"type": "domain", "allowed_domains": allowed, "blocked_domains": blocked}


async def content_type_filter_tool(allowed: List[str]):
    """
    This tool constructs a filter that allows crawling based on the MIME content type
    of the web resources. It helps in focusing the crawl on specific types of
    content, such as HTML pages or PDF documents.

    Args:
        allowed (List[str]): A list of allowed MIME types (e.g.,
                             "text/html", "application/json"). Only URLs whose
                             content type matches one of these will be processed.

    Returns:
        dict: A dictionary representing the configuration for a content type filter.
              This dictionary includes the filter type ("content_type") and a list
              of allowed MIME types.
              Example: `{"type": "content_type", "allowed_types": ["text/html"]}`
    """
    print(f"Constructing content type filter for crawler...")
    return {"type": "content_type", "allowed_types": allowed}
