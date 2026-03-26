"""SQLite-backed cache for web search results.

Caches (query, num_results, provider) tuples with a configurable TTL.
Used by web_tools.web_search() to avoid redundant API calls.

Cache is stored independently of the main SQLAlchemy database so the
tools layer stays decoupled from the storage layer.

Default path: ~/.configurable_agents/web_search_cache.db
Default TTL:  3600 seconds (1 hour)

Example:
    >>> cache = WebSearchCache(db_path="/tmp/test_cache.db", ttl_seconds=60)
    >>> cache.set("python news", 5, "serper", {"results": [...], "provider": "serper"})
    >>> cached = cache.get("python news", 5, "serper")
    >>> cached is not None
    True
"""

import hashlib
import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS web_search_cache (
    cache_key   TEXT    PRIMARY KEY,
    query       TEXT    NOT NULL,
    num_results INTEGER NOT NULL,
    provider    TEXT    NOT NULL,
    results_json TEXT   NOT NULL,
    created_at  REAL    NOT NULL,
    expires_at  REAL    NOT NULL
)
"""


class WebSearchCache:
    """SQLite-backed cache for web search results.

    Each entry is keyed by a SHA-256 hash of (provider, num_results, query)
    and expires after ttl_seconds.

    Thread-safety: sqlite3 connections are created per-call (not shared),
    which is safe for multi-threaded use within a single process.
    """

    def __init__(self, db_path: str, ttl_seconds: int = 3600):
        """Initialise the cache.

        Args:
            db_path: Filesystem path to the SQLite database file.
                     Parent directory is created automatically if missing.
            ttl_seconds: Time-to-live for cache entries in seconds (default: 3600).
        """
        self.db_path = db_path
        self.ttl = ttl_seconds
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(_CREATE_TABLE_SQL)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    @staticmethod
    def _make_key(query: str, num_results: int, provider: str) -> str:
        raw = f"{provider}:{num_results}:{query}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, query: str, num_results: int, provider: str) -> Optional[Dict[str, Any]]:
        """Return cached result, or None if missing or expired.

        Args:
            query: The search query string.
            num_results: Number of results that was requested.
            provider: Provider name used for the search (e.g. "serper").

        Returns:
            Cached result dict, or None on cache miss / expiry.
        """
        key = self._make_key(query, num_results, provider)
        now = time.time()

        with self._connect() as conn:
            row = conn.execute(
                "SELECT results_json, expires_at FROM web_search_cache WHERE cache_key = ?",
                (key,),
            ).fetchone()

        if row is None:
            return None

        results_json, expires_at = row
        if now > expires_at:
            with self._connect() as conn:
                conn.execute(
                    "DELETE FROM web_search_cache WHERE cache_key = ?", (key,)
                )
            logger.debug(f"Cache entry expired for query='{query}' provider={provider}")
            return None

        return json.loads(results_json)

    def set(self, query: str, num_results: int, provider: str, result: Dict[str, Any]) -> None:
        """Store a search result in the cache.

        Args:
            query: The search query string.
            num_results: Number of results that was requested.
            provider: Provider name used (e.g. "serper").
            result: The full result dict returned by the search provider.
        """
        key = self._make_key(query, num_results, provider)
        now = time.time()

        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO web_search_cache
                    (cache_key, query, num_results, provider, results_json, created_at, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (key, query, num_results, provider, json.dumps(result), now, now + self.ttl),
            )

    def clear_expired(self) -> int:
        """Delete all expired cache entries.

        Returns:
            Number of entries deleted.
        """
        now = time.time()
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM web_search_cache WHERE expires_at < ?", (now,)
            )
            return cursor.rowcount
