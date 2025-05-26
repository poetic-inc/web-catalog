from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from crawl4ai import URLFilter

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
