# T-016: Web Search Enterprise Hardening

**Status**: DONE (2026-03-26)
**Priority**: MEDIUM
**Created**: 2026-03-23

---

## Problem

The current `web_search` tool (`tools/web_tools.py`) is minimal:
- No retry on transient API failures (single attempt, hard fail)
- No fallback if primary provider is down
- No caching — same query hits Serper/Tavily on every workflow run
- No minimum result validation — returns empty results silently
- Timeout is hardcoded at 10s, not configurable
- No per-run search call cap

For GTM workflows running multiple times per day on similar topics, this creates unnecessary API cost and fragility. For complex workflows with search loops, a single transient Serper failure aborts the entire run.

---

## Success Criteria

- Transient Serper/Tavily failures retry automatically (3 attempts, exponential backoff)
- If primary provider exhausts retries, falls back to secondary provider if configured
- Identical `(query, num_results)` within the same run hits cache, not the API
- Cross-run cache with configurable TTL (default: 1 hour) stored in SQLite
- Explicit error if result count < `min_results` (default: 1)
- All new config fields are optional — zero breaking changes to existing configs

---

## Implementation Approach

### Step 1: Add retry logic to `_serper_search()` and `_tavily_search()`

**File**: `src/configurable_agents/tools/web_tools.py`

```python
import time

def _serper_search_with_retry(query: str, num_results: int, max_attempts: int = 3, backoff_factor: float = 1.5) -> Dict[str, Any]:
    last_error = None
    for attempt in range(max_attempts):
        try:
            result = _serper_search(query, num_results)
            if result.get("error") is None:
                return result
            last_error = result.get("error")
        except Exception as e:
            last_error = str(e)

        if attempt < max_attempts - 1:
            wait = backoff_factor ** attempt
            logger.warning(f"Serper search attempt {attempt + 1} failed: {last_error}. Retrying in {wait:.1f}s...")
            time.sleep(wait)

    return {"results": [], "error": f"All {max_attempts} attempts failed: {last_error}", "provider": "serper"}
```

Same pattern for Tavily.

### Step 2: Provider fallback

**File**: `src/configurable_agents/tools/web_tools.py`

Update `web_search()` to try fallback:
```python
def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    primary = _get_search_provider()
    fallback = os.getenv("WEB_SEARCH_FALLBACK_PROVIDER")

    result = _search_with_provider(primary, query, num_results)

    if result.get("error") and fallback and fallback != primary:
        logger.warning(f"Primary provider '{primary}' failed, trying fallback '{fallback}'")
        result = _search_with_provider(fallback, query, num_results)

    return result
```

### Step 3: SQLite-backed query cache

**File**: `src/configurable_agents/tools/web_search_cache.py` (new)

```python
class WebSearchCache:
    """SQLite-backed cache for web search results."""

    def __init__(self, db_path: str, ttl_seconds: int = 3600):
        self.db_path = db_path
        self.ttl = ttl_seconds
        self._init_db()

    def get(self, query: str, num_results: int, provider: str) -> Optional[Dict]:
        cache_key = self._key(query, num_results, provider)
        # SELECT from cache, check expiry, return if fresh

    def set(self, query: str, num_results: int, provider: str, results: Dict) -> None:
        cache_key = self._key(query, num_results, provider)
        # INSERT OR REPLACE with timestamp

    def _key(self, query: str, num_results: int, provider: str) -> str:
        import hashlib
        return hashlib.sha256(f"{provider}:{num_results}:{query}".encode()).hexdigest()
```

Cache is stored in the same SQLite DB as the rest of the system (`configurable_agents.db`). New table: `web_search_cache(cache_key, query, provider, results_json, created_at, expires_at)`.

Cache is opt-in via `WEB_SEARCH_CACHE_ENABLED=true` env var or tool config. Default: off in v1.1 (avoids migration complexity), on in v1.2 after stabilization.

Actually, reconsider: cache is high-value for development iteration. Make it **on by default** with TTL=1h, with opt-out via `WEB_SEARCH_CACHE_ENABLED=false`.

### Step 4: Result validation

**File**: `src/configurable_agents/tools/web_tools.py`

```python
MIN_RESULTS_DEFAULT = 1

def web_search(query: str, num_results: int = 10) -> Dict[str, Any]:
    ...
    min_results = int(os.getenv("WEB_SEARCH_MIN_RESULTS", MIN_RESULTS_DEFAULT))

    if not result.get("error") and len(result.get("results", [])) < min_results:
        result["error"] = (
            f"Search returned {len(result.get('results', []))} results, "
            f"minimum required: {min_results}. Query: '{query}'"
        )
        logger.warning(result["error"])

    return result
```

### Step 5: Tool-level configuration (YAML)

For full configurability from YAML, tool config can pass overrides when creating the tool:
```yaml
nodes:
  - id: search
    tools:
      - name: web_search
        config:
          max_attempts: 3
          backoff_factor: 1.5
          min_results: 3
          cache_ttl: 3600
```

The `ToolConfig.config` dict is passed to the factory. Update `create_web_search()` to accept and apply this config.

---

## Files to Change

| File | Change |
|------|--------|
| `src/configurable_agents/tools/web_tools.py` | Add retry, fallback, validation |
| `src/configurable_agents/tools/web_search_cache.py` | New: SQLite cache implementation |
| Storage schema | New `web_search_cache` table migration |
| `src/configurable_agents/tools/registry.py` | Pass tool config to `create_web_search()` |

---

## Implementation Order

1. Retry logic (highest value, lowest risk — pure addition)
2. Result validation (small addition)
3. Provider fallback (medium complexity)
4. SQLite cache (most complex — requires migration)

Can ship retry + validation first in one PR, then fallback + cache in a second.

---

## Testing Strategy

**Unit tests**:
- Mock Serper to fail twice, succeed on third → verify retry behavior, correct result returned
- Mock Serper to fail all attempts → verify fallback to Tavily called
- Mock empty results → verify validation error logged and returned

**Integration tests**:
- Live Serper call (requires API key in test env) → verify retry doesn't trigger on success
- Cache: same query twice within TTL → verify second call doesn't hit API (mock API to verify call count)

---

## Notes

- Environment variables for quick configuration without YAML changes:
  - `WEB_SEARCH_MAX_ATTEMPTS=3`
  - `WEB_SEARCH_BACKOFF_FACTOR=1.5`
  - `WEB_SEARCH_FALLBACK_PROVIDER=tavily`
  - `WEB_SEARCH_CACHE_ENABLED=true`  ← ON by default; set to `false` to opt-out
  - `WEB_SEARCH_CACHE_TTL=3600`
  - `WEB_SEARCH_CACHE_PATH=~/.configurable_agents/web_search_cache.db`
  - `WEB_SEARCH_MIN_RESULTS=1`
- The cache significantly reduces development cost — iterating on a research workflow with the same test topic won't hit Serper on every test run
- YAML per-node tool config (Step 5) deferred to AX-017 — requires changing the registry's `ToolFactory` signature

## Actual Implementation (2026-03-26)

**Files changed**:
- `src/configurable_agents/tools/web_search_cache.py` — NEW. `WebSearchCache` class with sqlite3 backend (get/set/clear_expired). Standalone DB file, decoupled from SQLAlchemy storage layer.
- `src/configurable_agents/tools/web_tools.py` — Added `_search_with_retry()`, `_get_cache()`, `_reset_cache()`, updated `web_search()` with retry→fallback→cache→validation flow.
- `tests/tools/test_web_search_cache.py` — NEW. 7 unit tests (miss, hit, expiry, key isolation, upsert).
- `tests/tools/test_web_tools.py` — Added `TestWebSearchRetryAndFallback` with 11 tests.

**Key decisions made**:
- Cache ON by default (TTL=1h) — high dev iteration value
- Cache uses standalone sqlite3 (not SQLAlchemy) — keeps tools layer decoupled
- `ToolConfigError` never retried — propagates immediately from `_search_with_retry`
- Fallback `ToolConfigError` is caught and logged — primary error is preserved
- YAML tool config deferred to AX-017

**Test results**: 358 tools+core tests pass (0 failures)
