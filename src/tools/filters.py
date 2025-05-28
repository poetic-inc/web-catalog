from typing import List, Optional

from crawl4ai.deep_crawling.filters import (
    ContentTypeFilter,
    DomainFilter,
    FilterChain,
    URLPatternFilter,
)


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
        URLPatternFilter: An instance of the crawl4ai URLPatternFilter
                          configured with the provided patterns.
    """
    url_filter = URLPatternFilter(patterns=patterns)
    return url_filter


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
        DomainFilter: An instance of the crawl4ai DomainFilter configured
                      with the provided allowed and blocked domains.
    """
    domain_filter = DomainFilter(allowed_domains=allowed, blocked_domains=blocked)
    return domain_filter


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
        ContentTypeFilter: An instance of the crawl4ai ContentTypeFilter
                           configured with the provided allowed content types.
    """
    content_filter = ContentTypeFilter(allowed_types=allowed)
    return content_filter


# async def filter_generation_tool(
#     url_filter_args: Optional[dict] = None,
#     domain_filter_args: Optional[dict] = None,
#     content_type_filter_args: Optional[dict] = None,
# ) -> List:
#     """
#     Constructs a list of crawl4ai filter instances based on provided arguments.

#     This tool is designed to be called by an LLM or a higher-level agent
#     to dynamically create filters for web crawling tasks based on user
#     instructions or inferred requirements. Each argument corresponds to a
#     specific type of filter from the crawl4ai library. The created filters
#     can then be used in a crawl4ai FilterChain.

#     Args:
#         url_filter_args (Optional[dict]): Arguments for creating a
#             If provided, it should be a dictionary with the following key:
#             - "patterns" (List[str]): A list of wildcard or regex patterns. URLs matching
#               any of these patterns will be processed by the crawler if this
#               filter is applied.
#               Example: `{"patterns": [".*example.com/products/.*", ".*category/items/.*"]}`

#         domain_filter_args (Optional[dict]): Arguments for creating a
#             If provided, it should be a dictionary with one or both of the
#             following keys:
#             - "allowed" (List[str]): A list of domain names (e.g., "example.com")
#               from which URLs are allowed.
#             - "blocked" (List[str]): A list of domain names from which URLs are
#               blocked.
#             Example: `{"allowed": ["example.com", "another.org"], "blocked": ["ads.example.com"]}`

#         content_type_filter_args (Optional[dict]): Arguments for creating a
#             If provided, it should be a dictionary with the following key:
#             - "allowed" (List[str]): A list of allowed MIME types (e.g.,
#               "text/html", "application/json"). Only URLs whose content type
#               matches one of these will be processed.
#             Example: `{"allowed": ["text/html", "application/pdf"]}`

#     Returns:
#         List[URLFilter]: A list containing the configured filter instances.
#                          Returns an empty list if no arguments are provided or if
#                          the provided arguments do not lead to the creation of any filters.
#     """
#     filters = []

#     if url_filter_args:
#         patterns = url_filter_args["patterns"]
#         url_filter = URLPatternFilter(patterns=patterns)
#         filters.extend(url_filter)

#     if domain_filter_args:
#         allowed = (domain_filter_args["allowed"],)
#         blocked = (domain_filter_args["blocked"],)
#         domain_filter = DomainFilter(
#             allowed_domains=allowed,
#             blocked_domains=blocked,
#         )
#         filters.extend(domain_filter)

#     if content_type_filter_args:
#         allowed = content_type_filter_args["allowed"]
#         content_type_filter = ContentTypeFilter(allowed_types=allowed)
#         filters.extend(content_type_filter)

#     return filters
