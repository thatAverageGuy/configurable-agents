"""Tests for web tools implementation."""

from unittest.mock import MagicMock, Mock, patch, call

import pytest

from configurable_agents.tools import list_tools
from configurable_agents.tools.registry import ToolConfigError
from configurable_agents.tools.web_tools import (
    web_search,
    web_scrape,
    http_client,
    create_web_search,
    create_web_scrape,
    create_http_client,
    _reset_cache,
)


class TestWebSearchTool:
    """Tests for web_search tool."""

    def test_list_includes_web_search(self):
        """Test that web_search is in the tool registry."""
        tools = list_tools()
        assert "web_search" in tools

    @pytest.mark.integration
    def test_web_search_requires_api_key(self, monkeypatch):
        """Test that web_search requires API key."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")

        with pytest.raises(ToolConfigError) as exc_info:
            web_search("test query")

        assert "SERPER_API_KEY" in str(exc_info.value)

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_web_search_with_mock_api(self, mock_post, monkeypatch):
        """Test web_search with mocked API response."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")

        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "organic": [
                        {
                            "title": "Test Result 1",
                            "link": "https://example.com/1",
                            "snippet": "Test snippet 1",
                        },
                        {
                            "title": "Test Result 2",
                            "link": "https://example.com/2",
                            "snippet": "Test snippet 2",
                        },
                    ],
                    "answerBox": {
                        "answer": "Quick answer",
                    },
                }
            def raise_for_status(self):
                pass

        mock_post.return_value = MockResponse()

        result = web_search("test query", num_results=5)

        assert "results" in result
        assert len(result["results"]) >= 2
        assert result["provider"] == "serper"
        assert result["results"][0]["title"] == "Answer"
        assert result["results"][1]["title"] == "Test Result 1"

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_web_search_handles_http_errors(self, mock_post, monkeypatch):
        """Test web_search handles HTTP errors gracefully."""
        import requests

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")

        mock_post.side_effect = requests.RequestException("Network error")

        result = web_search("test query")

        assert "error" in result
        assert result["results"] == []

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_web_search_respects_num_results(self, mock_post, monkeypatch):
        """Test that num_results parameter limits results."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")

        class MockResponse:
            status_code = 200
            def json(self):
                return {
                    "organic": [
                        {"title": f"Result {i}", "link": f"https://example.com/{i}", "snippet": f"Snippet {i}"}
                        for i in range(10)
                    ]
                }
            def raise_for_status(self):
                pass

        mock_post.return_value = MockResponse()

        result = web_search("test query", num_results=3)

        assert len([r for r in result["results"] if r["title"] != "Answer"]) <= 3

    def test_web_search_unsupported_provider(self, monkeypatch):
        """Test web_search with unsupported provider."""
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "unsupported")

        with pytest.raises(ToolConfigError) as exc_info:
            web_search("test query")

        assert "Unsupported search provider" in str(exc_info.value)


class TestWebScrapeTool:
    """Tests for web_scrape tool."""

    def test_list_includes_web_scrape(self):
        """Test that web_scrape is in the tool registry."""
        tools = list_tools()
        assert "web_scrape" in tools

    @patch("configurable_agents.tools.web_tools.requests.get")
    def test_web_scrape_basic(self, mock_get):
        """Test basic web scraping."""
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is test content.</p>
            </body>
        </html>
        """

        class MockResponse:
            status_code = 200
            @property
            def content(self):
                return html.encode('utf-8')
            def raise_for_status(self):
                pass

        mock_get.return_value = MockResponse()

        result = web_scrape("https://example.com")

        assert result["url"] == "https://example.com"
        assert result["title"] == "Test Page"
        assert "test content" in result["content"].lower()
        assert result["error"] is None

    @patch("configurable_agents.tools.web_tools.requests.get")
    def test_web_scrape_with_selector(self, mock_get):
        """Test web scraping with CSS selector."""
        html = """
        <html>
            <body>
                <article><p>First paragraph</p></article>
                <div><p>Second paragraph</p></div>
            </body>
        </html>
        """

        class MockResponse:
            status_code = 200
            @property
            def content(self):
                return html.encode('utf-8')
            def raise_for_status(self):
                pass

        mock_get.return_value = MockResponse()

        result = web_scrape("https://example.com", selector="article p")

        assert "First paragraph" in result["content"]
        assert "Second paragraph" not in result["content"]

    @patch("configurable_agents.tools.web_tools.requests.get")
    def test_web_scrape_handles_http_errors(self, mock_get):
        """Test web_scrape handles HTTP errors."""
        mock_get.side_effect = Exception("Connection failed")

        result = web_scrape("https://example.com")

        assert result["error"] is not None
        assert result["content"] == ""

    @patch("configurable_agents.tools.web_tools.requests.get")
    def test_web_scrape_limits_content_size(self, mock_get):
        """Test that web_scrape limits large content."""
        large_html = "<html><body>" + "x" * 20000 + "</body></html>"

        class MockResponse:
            status_code = 200
            @property
            def content(self):
                return large_html.encode('utf-8')
            def raise_for_status(self):
                pass

        mock_get.return_value = MockResponse()

        result = web_scrape("https://example.com")

        assert len(result["content"]) <= 10000


class TestHttpClientTool:
    """Tests for http_client tool."""

    def test_list_includes_http_client(self):
        """Test that http_client is in the tool registry."""
        tools = list_tools()
        assert "http_client" in tools

    @patch("configurable_agents.tools.web_tools.requests.request")
    def test_http_get(self, mock_request):
        """Test HTTP GET request."""
        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "application/json"}
            def json(self):
                return {"status": "ok"}
            def raise_for_status(self):
                pass

        mock_request.return_value = MockResponse()

        result = http_client("GET", "https://api.example.com/data")

        assert result["status_code"] == 200
        assert result["body"]["status"] == "ok"
        assert result["error"] is None

    @patch("configurable_agents.tools.web_tools.requests.request")
    def test_http_post_with_json_body(self, mock_request):
        """Test HTTP POST with JSON body."""
        class MockResponse:
            status_code = 201
            headers = {"Content-Type": "application/json"}
            def json(self):
                return {"id": 123}
            def raise_for_status(self):
                pass

        mock_request.return_value = MockResponse()

        result = http_client("POST", "https://api.example.com/create", body={"name": "test"})

        assert result["status_code"] == 201
        assert result["body"]["id"] == 123

    @patch("configurable_agents.tools.web_tools.requests.request")
    def test_http_client_with_text_response(self, mock_request):
        """Test HTTP client with non-JSON response."""
        class MockResponse:
            status_code = 200
            headers = {"Content-Type": "text/plain"}
            text = "Plain text response"
            def json(self):
                raise ValueError("Not JSON")
            def raise_for_status(self):
                pass

        mock_request.return_value = MockResponse()

        result = http_client("GET", "https://example.com")

        assert result["status_code"] == 200
        assert result["body"] == "Plain text response"

    def test_http_client_invalid_method(self):
        """Test http_client rejects invalid HTTP methods."""
        result = http_client("INVALID", "https://example.com")

        assert result["status_code"] == 0
        assert "Invalid method" in result["error"]

    @patch("configurable_agents.tools.web_tools.requests.request")
    def test_http_client_handles_network_errors(self, mock_request):
        """Test http_client handles network errors."""
        mock_request.side_effect = Exception("Network error")

        result = http_client("GET", "https://example.com")

        assert result["status_code"] == 0
        assert result["error"] is not None


class TestWebSearchRetryAndFallback:
    """Tests for retry, fallback, validation, and cache integration in web_search."""

    def setup_method(self):
        _reset_cache()

    def _make_mock_response(self, organic=None, raise_exc=None):
        """Build a mock requests.Response for Serper."""
        class MockResponse:
            status_code = 200
            def json(self):
                return {"organic": organic or []}
            def raise_for_status(self):
                if raise_exc:
                    raise raise_exc

        return MockResponse()

    @patch("configurable_agents.tools.web_tools.time.sleep")
    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_retry_succeeds_on_third_attempt(self, mock_post, mock_sleep, monkeypatch):
        """Fails twice then succeeds — result from third attempt returned."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "3")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.side_effect = [
            req.RequestException("timeout"),
            req.RequestException("timeout"),
            self._make_mock_response(organic=[
                {"title": "Ok", "link": "https://ok.com", "snippet": "ok"}
            ]),
        ]

        result = web_search("python", num_results=1)

        assert result.get("error") is None
        assert result["results"][0]["title"] == "Ok"
        assert mock_post.call_count == 3
        assert mock_sleep.call_count == 2

    @patch("configurable_agents.tools.web_tools.time.sleep")
    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_retry_exhausted_returns_error(self, mock_post, mock_sleep, monkeypatch):
        """All attempts fail — error dict returned (no exception raised)."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "3")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")
        monkeypatch.delenv("WEB_SEARCH_FALLBACK_PROVIDER", raising=False)

        mock_post.side_effect = req.RequestException("network down")

        result = web_search("python", num_results=5)

        assert result.get("error") is not None
        assert result["results"] == []
        assert mock_post.call_count == 3

    @patch("configurable_agents.tools.web_tools.time.sleep")
    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_no_sleep_on_single_attempt(self, mock_post, mock_sleep, monkeypatch):
        """With max_attempts=1 no retry sleep should occur."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")
        monkeypatch.delenv("WEB_SEARCH_FALLBACK_PROVIDER", raising=False)

        mock_post.side_effect = req.RequestException("fail")

        web_search("python")

        mock_sleep.assert_not_called()

    @patch("configurable_agents.tools.web_tools.time.sleep")
    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_fallback_used_when_primary_fails(self, mock_post, mock_sleep, monkeypatch):
        """Primary (serper) exhausts retries; fallback (tavily) succeeds."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_FALLBACK_PROVIDER", "tavily")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.side_effect = req.RequestException("serper down")

        tavily_result = {"results": [{"title": "Tavily", "url": "https://t.com", "snippet": "t"}], "provider": "tavily"}

        with patch("configurable_agents.tools.web_tools._tavily_search", return_value=tavily_result):
            result = web_search("python")

        assert result["provider"] == "tavily"
        assert result.get("error") is None

    @patch("configurable_agents.tools.web_tools.time.sleep")
    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_no_fallback_when_not_configured(self, mock_post, mock_sleep, monkeypatch):
        """Primary fails, no fallback env var — primary error is returned."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.delenv("WEB_SEARCH_FALLBACK_PROVIDER", raising=False)
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.side_effect = req.RequestException("serper down")

        with patch("configurable_agents.tools.web_tools._tavily_search") as mock_tavily:
            result = web_search("python")
            mock_tavily.assert_not_called()

        assert result.get("error") is not None

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_fallback_toolconfigerror_keeps_primary_error(self, mock_post, monkeypatch):
        """Fallback raises ToolConfigError (not configured) — primary error kept."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_FALLBACK_PROVIDER", "tavily")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.side_effect = req.RequestException("serper down")

        with patch(
            "configurable_agents.tools.web_tools._tavily_search",
            side_effect=ToolConfigError("web_search", "TAVILY_API_KEY not set", "TAVILY_API_KEY"),
        ):
            result = web_search("python")

        assert result.get("error") is not None
        assert "serper" in result.get("provider", "")

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_min_results_validation_adds_error(self, mock_post, monkeypatch):
        """Empty results below min_results threshold → error key added."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_MIN_RESULTS", "3")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.return_value = self._make_mock_response(organic=[
            {"title": "Only one", "link": "https://x.com", "snippet": "x"}
        ])

        result = web_search("python", num_results=1)

        assert result.get("error") is not None
        assert "minimum required: 3" in result["error"]

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_min_results_validation_passes(self, mock_post, monkeypatch):
        """Results at or above threshold → no error added."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_MIN_RESULTS", "1")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "false")

        mock_post.return_value = self._make_mock_response(organic=[
            {"title": "Result", "link": "https://x.com", "snippet": "x"}
        ])

        result = web_search("python", num_results=1)

        assert result.get("error") is None

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_cache_hit_skips_api_call(self, mock_post, monkeypatch, tmp_path):
        """Second identical call hits cache — API not called again."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "true")
        monkeypatch.setenv("WEB_SEARCH_CACHE_PATH", str(tmp_path / "cache.db"))
        monkeypatch.setenv("WEB_SEARCH_MIN_RESULTS", "1")

        mock_post.return_value = self._make_mock_response(organic=[
            {"title": "Cached", "link": "https://x.com", "snippet": "x"}
        ])

        # First call — hits API
        r1 = web_search("python", num_results=5)
        # Second call — should be served from cache
        r2 = web_search("python", num_results=5)

        assert mock_post.call_count == 1
        assert r1 == r2

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_cache_miss_populates_cache(self, mock_post, monkeypatch, tmp_path):
        """Successful API call is stored so the next call is a cache hit."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "true")
        monkeypatch.setenv("WEB_SEARCH_CACHE_PATH", str(tmp_path / "cache.db"))
        monkeypatch.setenv("WEB_SEARCH_MIN_RESULTS", "1")

        mock_post.return_value = self._make_mock_response(organic=[
            {"title": "New", "link": "https://x.com", "snippet": "x"}
        ])

        web_search("unique query abc", num_results=3)
        assert mock_post.call_count == 1

        # Directly verify the cache holds the entry
        from configurable_agents.tools.web_search_cache import WebSearchCache
        cache = WebSearchCache(db_path=str(tmp_path / "cache.db"))
        assert cache.get("unique query abc", 3, "serper") is not None

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_failed_result_not_cached(self, mock_post, monkeypatch, tmp_path):
        """Error results are not stored in the cache."""
        import requests as req

        monkeypatch.setenv("SERPER_API_KEY", "test-key")
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")
        monkeypatch.setenv("WEB_SEARCH_MAX_ATTEMPTS", "1")
        monkeypatch.setenv("WEB_SEARCH_CACHE_ENABLED", "true")
        monkeypatch.setenv("WEB_SEARCH_CACHE_PATH", str(tmp_path / "cache.db"))
        monkeypatch.delenv("WEB_SEARCH_FALLBACK_PROVIDER", raising=False)

        mock_post.side_effect = req.RequestException("fail")

        web_search("error query", num_results=5)

        from configurable_agents.tools.web_search_cache import WebSearchCache
        cache = WebSearchCache(db_path=str(tmp_path / "cache.db"))
        assert cache.get("error query", 5, "serper") is None


class TestToolCreation:
    """Tests for tool factory functions."""

    def test_create_web_search_requires_api_key(self, monkeypatch):
        """Test create_web_search requires API key."""
        monkeypatch.delenv("SERPER_API_KEY", raising=False)
        monkeypatch.delenv("TAVILY_API_KEY", raising=False)
        monkeypatch.setenv("WEB_SEARCH_PROVIDER", "serper")

        with pytest.raises(ToolConfigError):
            create_web_search()

    def test_create_web_scrape_always_works(self):
        """Test create_web_scrape doesn't require config."""
        tool = create_web_scrape()
        assert tool.name == "web_scrape"

    def test_create_http_client_always_works(self):
        """Test create_http_client doesn't require config."""
        tool = create_http_client()
        assert tool.name == "http_client"

    @patch("configurable_agents.tools.web_tools.requests.post")
    def test_web_search_tool_callable(self, mock_post, monkeypatch):
        """Test web_search tool is callable."""
        monkeypatch.setenv("SERPER_API_KEY", "test-key")

        class MockResponse:
            status_code = 200
            def json(self):
                return {"organic": []}
            def raise_for_status(self):
                pass

        mock_post.return_value = MockResponse()

        tool = create_web_search()

        # Test with dict input
        result = tool.func({"query": "test"})
        assert "results" in result

        # Test with string input
        result = tool.func("test")
        assert "results" in result

    @patch("configurable_agents.tools.web_tools.requests.get")
    def test_web_scrape_tool_callable(self, mock_get):
        """Test web_scrape tool is callable."""
        html = "<html><body>Test</body></html>"

        class MockResponse:
            status_code = 200
            @property
            def content(self):
                return html.encode('utf-8')
            def raise_for_status(self):
                pass

        mock_get.return_value = MockResponse()

        tool = create_web_scrape()

        # Test with dict input
        result = tool.func({"url": "https://example.com"})
        assert "url" in result

    def test_http_client_tool_callable(self):
        """Test http_client tool is callable."""
        tool = create_http_client()

        # http_client requires method and url
        result = tool.func({
            "method": "GET",
            "url": "https://example.com",
        })
        # The result will have an error since we're not mocking, but check structure
        assert "status_code" in result
