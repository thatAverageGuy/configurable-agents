"""Tests for web tools implementation."""

from unittest.mock import Mock, patch

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
