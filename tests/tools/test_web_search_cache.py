"""Tests for WebSearchCache."""

import time

import pytest

from configurable_agents.tools.web_search_cache import WebSearchCache


SAMPLE_RESULT = {"results": [{"title": "T1", "url": "https://x.com", "snippet": "s"}], "provider": "serper"}


@pytest.fixture
def cache(tmp_path):
    return WebSearchCache(db_path=str(tmp_path / "cache.db"), ttl_seconds=60)


class TestWebSearchCache:

    def test_miss_returns_none(self, cache):
        assert cache.get("python news", 5, "serper") is None

    def test_set_then_get_returns_data(self, cache):
        cache.set("python news", 5, "serper", SAMPLE_RESULT)
        result = cache.get("python news", 5, "serper")
        assert result == SAMPLE_RESULT

    def test_expired_entry_returns_none(self, tmp_path):
        short_cache = WebSearchCache(db_path=str(tmp_path / "cache.db"), ttl_seconds=0)
        short_cache.set("python news", 5, "serper", SAMPLE_RESULT)
        # TTL=0 means it expires immediately
        time.sleep(0.01)
        assert short_cache.get("python news", 5, "serper") is None

    def test_different_queries_do_not_collide(self, cache):
        r1 = {"results": [{"title": "A", "url": "", "snippet": ""}], "provider": "serper"}
        r2 = {"results": [{"title": "B", "url": "", "snippet": ""}], "provider": "serper"}
        cache.set("query A", 5, "serper", r1)
        cache.set("query B", 5, "serper", r2)
        assert cache.get("query A", 5, "serper") == r1
        assert cache.get("query B", 5, "serper") == r2

    def test_different_providers_do_not_collide(self, cache):
        r_serper = {"results": [], "provider": "serper"}
        r_tavily = {"results": [], "provider": "tavily"}
        cache.set("ai news", 5, "serper", r_serper)
        cache.set("ai news", 5, "tavily", r_tavily)
        assert cache.get("ai news", 5, "serper") == r_serper
        assert cache.get("ai news", 5, "tavily") == r_tavily

    def test_clear_expired_removes_stale_entries(self, tmp_path):
        short_cache = WebSearchCache(db_path=str(tmp_path / "cache.db"), ttl_seconds=0)
        short_cache.set("query A", 5, "serper", SAMPLE_RESULT)
        short_cache.set("query B", 5, "serper", SAMPLE_RESULT)
        time.sleep(0.01)
        deleted = short_cache.clear_expired()
        assert deleted == 2

    def test_insert_or_replace_updates_existing_entry(self, cache):
        old_result = {"results": [], "provider": "serper"}
        new_result = SAMPLE_RESULT
        cache.set("query", 5, "serper", old_result)
        cache.set("query", 5, "serper", new_result)
        assert cache.get("query", 5, "serper") == new_result
