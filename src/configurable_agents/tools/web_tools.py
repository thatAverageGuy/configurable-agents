"""Web tools for web search, scraping, and HTTP requests.

Provides three main tools:
- web_search: Search the web using Serper or Tavily API
- web_scrape: Extract text content from web pages
- http_client: Make HTTP requests with full control

web_search hardening (T-016):
- Retry on transient failures (WEB_SEARCH_MAX_ATTEMPTS, WEB_SEARCH_BACKOFF_FACTOR)
- Provider fallback if primary exhausts retries (WEB_SEARCH_FALLBACK_PROVIDER)
- SQLite-backed result cache, on by default (WEB_SEARCH_CACHE_ENABLED, WEB_SEARCH_CACHE_TTL, WEB_SEARCH_CACHE_PATH)
- Minimum result count validation (WEB_SEARCH_MIN_RESULTS)

Example:
    >>> from configurable_agents.tools import get_tool
    >>> search = get_tool("web_search")
    >>> results = search.run({"query": "Python programming", "num_results": 5})
"""

import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

from langchain_core.tools import Tool

from configurable_agents.tools.registry import ToolConfigError, ToolFactory

logger = logging.getLogger(__name__)

# Web search provider configuration
SEARCH_PROVIDERS = ["serper", "tavily"]
DEFAULT_PROVIDER = "serper"

# Module-level cache singleton — reset via _reset_cache() in tests
_cache_instance: Optional[Any] = None


def _get_search_provider() -> str:
    """Get the configured web search provider.

    Reads from WEB_SEARCH_PROVIDER env var, defaults to 'serper'.

    Returns:
        Provider name (serper or tavily)
    """
    return os.getenv("WEB_SEARCH_PROVIDER", DEFAULT_PROVIDER).lower()


def _get_cache() -> Optional[Any]:
    """Return the active WebSearchCache instance, or None if caching is disabled.

    Cache is enabled by default. Set WEB_SEARCH_CACHE_ENABLED=false to opt out.
    """
    if os.getenv("WEB_SEARCH_CACHE_ENABLED", "true").lower() == "false":
        return None

    global _cache_instance
    if _cache_instance is None:
        from configurable_agents.tools.web_search_cache import WebSearchCache

        default_path = str(Path.home() / ".configurable_agents" / "web_search_cache.db")
        db_path = os.getenv("WEB_SEARCH_CACHE_PATH", default_path)
        ttl = int(os.getenv("WEB_SEARCH_CACHE_TTL", "3600"))
        _cache_instance = WebSearchCache(db_path=db_path, ttl_seconds=ttl)

    return _cache_instance


def _reset_cache() -> None:
    """Reset the cache singleton. Intended for use in tests only."""
    global _cache_instance
    _cache_instance = None


def _search_with_retry(
    provider: str,
    query: str,
    num_results: int,
    max_attempts: int,
    backoff_factor: float,
) -> Dict[str, Any]:
    """Call the given provider with exponential-backoff retry.

    ToolConfigError (missing API key, missing package) propagates immediately
    — it is a configuration problem, not a transient failure, and retrying
    would never help.

    Args:
        provider: "serper" or "tavily"
        query: Search query string
        num_results: Number of results requested
        max_attempts: Maximum number of attempts (1 = no retry)
        backoff_factor: Sleep multiplier between attempts (attempt 0 → factor^0 s, etc.)

    Returns:
        Result dict from the provider (may contain "error" key on failure)

    Raises:
        ToolConfigError: Immediately if the provider is mis-configured.
    """
    if provider == "serper":
        search_fn = _serper_search
    elif provider == "tavily":
        search_fn = _tavily_search
    else:
        raise ToolConfigError(
            tool_name="web_search",
            reason=f"Unsupported search provider: {provider}",
            env_var="WEB_SEARCH_PROVIDER",
        )

    last_result: Dict[str, Any] = {"results": [], "error": f"No attempts made", "provider": provider}

    for attempt in range(max_attempts):
        # ToolConfigError propagates immediately (not caught here)
        result = search_fn(query, num_results)

        if not result.get("error"):
            return result

        last_result = result

        if attempt < max_attempts - 1:
            wait = backoff_factor ** attempt
            logger.warning(
                f"[web_search/{provider}] Attempt {attempt + 1}/{max_attempts} failed: "
                f"{result.get('error')}. Retrying in {wait:.1f}s..."
            )
            time.sleep(wait)
        else:
            logger.error(
                f"[web_search/{provider}] All {max_attempts} attempts failed: "
                f"{result.get('error')}"
            )

    return last_result


def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    """Search the web using configured provider.

    Applies retry, provider fallback, result caching, and minimum result
    validation. All behaviour is controlled via environment variables —
    see module docstring for the full list.

    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)

    Returns:
        Dict with results list containing {title, url, snippet}.
        On failure: dict with empty "results" list and populated "error" key.

    Raises:
        ToolConfigError: If primary provider API key is not configured.

    Example:
        >>> result = web_search("Python best practices", num_results=5)
        >>> for item in result["results"]:
        ...     print(f"{item['title']}: {item['url']}")
    """
    provider = _get_search_provider()
    max_attempts = int(os.getenv("WEB_SEARCH_MAX_ATTEMPTS", "3"))
    backoff_factor = float(os.getenv("WEB_SEARCH_BACKOFF_FACTOR", "1.5"))
    min_results = int(os.getenv("WEB_SEARCH_MIN_RESULTS", "1"))

    # --- Cache check ---
    cache = _get_cache()
    if cache is not None:
        cached = cache.get(query, num_results, provider)
        if cached is not None:
            logger.debug(f"[web_search] Cache hit: query='{query}' provider={provider}")
            return cached

    # --- Primary provider with retry ---
    result = _search_with_retry(provider, query, num_results, max_attempts, backoff_factor)

    # --- Fallback provider ---
    if result.get("error"):
        fallback = os.getenv("WEB_SEARCH_FALLBACK_PROVIDER", "").strip().lower()
        if fallback and fallback != provider and fallback in SEARCH_PROVIDERS:
            logger.warning(
                f"[web_search] Primary '{provider}' failed, trying fallback '{fallback}'"
            )
            try:
                fallback_result = _search_with_retry(
                    fallback, query, num_results, max_attempts, backoff_factor
                )
                result = fallback_result
            except ToolConfigError as e:
                logger.warning(
                    f"[web_search] Fallback '{fallback}' not configured: {e}"
                )

    # --- Cache successful result ---
    if cache is not None and not result.get("error"):
        cache.set(query, num_results, result.get("provider", provider), result)

    # --- Minimum result validation ---
    actual_count = len(result.get("results", []))
    if not result.get("error") and actual_count < min_results:
        msg = (
            f"Search returned {actual_count} result(s), minimum required: {min_results}. "
            f"Query: '{query}'"
        )
        logger.warning(f"[web_search] {msg}")
        result["error"] = msg

    return result


def _serper_search(query: str, num_results: int) -> Dict[str, Any]:
    """Search using Serper.dev API.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        Dict with results list
    """
    api_key = os.getenv("SERPER_API_KEY")
    if not api_key:
        raise ToolConfigError(
            tool_name="web_search",
            reason="SERPER_API_KEY environment variable not set",
            env_var="SERPER_API_KEY",
        )

    url = "https://google.serper.dev/search"
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json",
    }
    payload = {"q": query, "num": num_results}

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Extract results
        results = []
        organic = data.get("organic", [])
        for item in organic[:num_results]:
            results.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })

        # Include answer box if available
        answer_box = data.get("answerBox")
        if answer_box:
            results.insert(0, {
                "title": "Answer",
                "url": "",
                "snippet": answer_box.get("answer") or answer_box.get("snippet", ""),
            })

        return {"results": results, "provider": "serper"}

    except requests.RequestException as e:
        logger.error(f"Serper API error: {e}")
        return {
            "results": [],
            "error": str(e),
            "provider": "serper",
        }


def _tavily_search(query: str, num_results: int) -> Dict[str, Any]:
    """Search using Tavily API.

    Args:
        query: Search query
        num_results: Number of results

    Returns:
        Dict with results list
    """
    try:
        from tavily import TavilyClient
    except ImportError:
        raise ToolConfigError(
            tool_name="web_search",
            reason="tavily-python package not installed. Install with: pip install tavily-python",
            env_var=None,
        )

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        raise ToolConfigError(
            tool_name="web_search",
            reason="TAVILY_API_KEY environment variable not set",
            env_var="TAVILY_API_KEY",
        )

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(query, max_results=num_results)

        # Extract results
        results = []
        for item in response.get("results", []):
            results.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("content", ""),
            })

        return {"results": results, "provider": "tavily"}

    except Exception as e:
        logger.error(f"Tavily API error: {e}")
        return {
            "results": [],
            "error": str(e),
            "provider": "tavily",
        }


def web_scrape(url: str, selector: Optional[str] = None) -> Dict[str, Any]:
    """Extract text content from a web page.

    Args:
        url: URL to scrape
        selector: Optional CSS selector for targeted extraction

    Returns:
        Dict with url, title, content, extracted_text

    Example:
        >>> result = web_scrape("https://example.com")
        >>> print(result["content"])
        >>> # With selector
        >>> result = web_scrape("https://example.com", selector="article p")
    """
    try:
        response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()

        from bs4 import BeautifulSoup
        # Use response.content (bytes) for better encoding handling
        soup = BeautifulSoup(response.content, "html.parser")

        # Extract title
        title_tag = soup.find("title")
        title = title_tag.get_text() if title_tag else ""

        # Extract content
        if selector:
            # Use CSS selector
            elements = soup.select(selector)
            content = "\n".join(el.get_text(strip=True) for el in elements)
        else:
            # Extract all text from body
            body = soup.find("body")
            content = body.get_text(separator="\n", strip=True) if body else ""

        return {
            "url": url,
            "title": title,
            "content": content[:10000],  # Limit content size
            "extracted_text": content[:5000] if selector else "",
            "error": None,
        }

    except requests.RequestException as e:
        logger.error(f"HTTP error scraping {url}: {e}")
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {
            "url": url,
            "title": "",
            "content": "",
            "error": str(e),
        }


def http_client(
    method: str,
    url: str,
    headers: Optional[Dict[str, str]] = None,
    body: Optional[Any] = None,
) -> Dict[str, Any]:
    """Make an HTTP request.

    Args:
        method: HTTP method (GET, POST, PUT, DELETE)
        url: Request URL
        headers: Optional request headers
        body: Optional request body

    Returns:
        Dict with status_code, headers, body, error

    Example:
        >>> result = http_client("GET", "https://api.example.com/data")
        >>> result = http_client("POST", "https://api.example.com/create",
        ...                      body={"name": "test"})
    """
    method = method.upper()
    allowed_methods = ["GET", "POST", "PUT", "DELETE", "PATCH"]

    if method not in allowed_methods:
        return {
            "status_code": 0,
            "headers": {},
            "body": "",
            "error": f"Invalid method: {method}. Allowed: {allowed_methods}",
        }

    try:
        # Prepare request
        req_headers = headers or {}
        if body and isinstance(body, dict):
            req_headers["Content-Type"] = "application/json"
            import json
            body = json.dumps(body)

        # Make request
        response = requests.request(
            method=method,
            url=url,
            headers=req_headers,
            data=body,
            timeout=30,
        )

        # Extract response headers
        resp_headers = dict(response.headers)

        # Try to parse JSON response
        try:
            resp_body = response.json()
        except:
            resp_body = response.text[:10000]  # Limit text size

        return {
            "status_code": response.status_code,
            "headers": resp_headers,
            "body": resp_body,
            "error": None,
        }

    except requests.RequestException as e:
        logger.error(f"HTTP request error: {e}")
        return {
            "status_code": 0,
            "headers": {},
            "body": "",
            "error": str(e),
        }
    except Exception as e:
        logger.error(f"Unexpected error in http_client: {e}")
        return {
            "status_code": 0,
            "headers": {},
            "body": "",
            "error": str(e),
        }


# Tool factory functions

def create_web_search() -> Tool:
    """Create web search tool.

    Returns:
        Tool instance

    Raises:
        ToolConfigError: If provider not configured
    """
    provider = _get_search_provider()
    api_key = os.getenv("SERPER_API_KEY") if provider == "serper" else os.getenv("TAVILY_API_KEY")

    if not api_key:
        env_var = "SERPER_API_KEY" if provider == "serper" else "TAVILY_API_KEY"
        raise ToolConfigError(
            tool_name="web_search",
            reason=f"{env_var} environment variable not set",
            env_var=env_var,
        )

    return Tool(
        name="web_search",
        description=(
            f"Search the web using {provider.capitalize()} API. "
            "Returns a list of search results with title, URL, and snippet. "
            "Input should be a dict with 'query' (required) and 'num_results' (optional, default 10)."
        ),
        func=lambda x: web_search(**x) if isinstance(x, dict) else web_search(x, 10),
    )


def create_web_scrape() -> Tool:
    """Create web scrape tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="web_scrape",
        description=(
            "Extract text content from a web page. "
            "Input should be a dict with 'url' (required) and 'selector' (optional CSS selector). "
            "Returns title, content, and extracted text."
        ),
        func=lambda x: web_scrape(**x) if isinstance(x, dict) else web_scrape(x),
    )


def create_http_client() -> Tool:
    """Create HTTP client tool.

    Returns:
        Tool instance
    """
    return Tool(
        name="http_client",
        description=(
            "Make an HTTP request. "
            "Input should be a dict with 'method' (required: GET, POST, PUT, DELETE), "
            "'url' (required), 'headers' (optional), and 'body' (optional). "
            "Returns status code, headers, and response body."
        ),
        func=lambda x: http_client(**x) if isinstance(x, dict) else http_client("GET", x),
    )


# Register tools
def register_tools(registry: Any) -> None:
    """Register all web tools.

    Args:
        registry: ToolRegistry instance
    """
    registry.register_tool("web_search", create_web_search)
    registry.register_tool("web_scrape", create_web_scrape)
    registry.register_tool("http_client", create_http_client)


__all__ = [
    "web_search",
    "web_scrape",
    "http_client",
    "create_web_search",
    "create_web_scrape",
    "create_http_client",
    "register_tools",
    "_reset_cache",
]
