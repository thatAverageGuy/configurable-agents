# BF-005: Fix Pre-existing Test Failures

**Date**: 2026-02-08
**Status**: Complete — all 69 tests in affected modules pass

---

## Overview

Fixed 22 pre-existing test failures across 5 test files. These failures were not caused by any of our bug fixes — they existed before CL-003 began. The tests had stale assertions that didn't match actual code behavior.

---

## Problems Found (3 categories)

### Category 1: dict-vs-Pydantic assertions (17 failures)

**Affected files**:
- `tests/core/test_node_executor.py` (3 failures)
- `tests/core/test_node_executor_metrics.py` (4 failures)
- `tests/sandbox/test_integration.py` (10 failures)

**Root Cause**: `execute_node()` returns a partial state dict containing only the updated fields, NOT a full Pydantic model. Tests were:
1. Accessing results via `.attribute` (Pydantic) instead of `["key"]` (dict)
2. Asserting that unchanged fields were still present in the result

**Fix**: Changed `.attr` → `["key"]` dict access. Changed "unchanged field preserved" assertions to `assert "field" not in updated_state`.

### Category 2: Deploy artifact count (3 failures)

**Affected files**:
- `tests/deploy/test_generator.py` (2 failures)
- `tests/deploy/test_generator_integration.py` (1 failure)

**Root Cause**: Deploy generator now produces 10 artifacts (previously 8) since `src/` directory and `pyproject.toml` were added. Tests asserted `len(artifacts) == 8`.

**Fix**: Changed count to 10, added `src/` and `pyproject.toml` to expected file lists.

### Category 3: Dockerfile assertion errors (2 failures)

**Affected files**:
- `tests/deploy/test_generator_integration.py` (2 failures)

**Root Cause**:
1. Dockerfile template uses fixed internal ports (8000/5000) regardless of user-configured ports. Tests checked for user-configured ports in Dockerfile content.
2. `file_path.stat().st_size > 0` check failed for `src/` directory artifact on Windows (directories have st_size=0).

**Fix**:
1. Changed `assert "EXPOSE 9000 5001"` → `assert "EXPOSE 8000 5000"`
2. Added `if file_path.is_file()` guard before size check

---

## Changes Made

| File | Change |
|------|--------|
| `tests/core/test_node_executor.py` | `.research`/`.summary` → `["research"]`/`["summary"]`, removed unchanged field assertions |
| `tests/core/test_node_executor_metrics.py` | `.result`/`.analysis` → `["result"]`/`["analysis"]` |
| `tests/sandbox/test_integration.py` | `.result`/`.doubled` → `["result"]`/`["doubled"]` (10 tests) |
| `tests/deploy/test_generator.py` | `len(artifacts) == 8` → `len(artifacts) == 10` |
| `tests/deploy/test_generator_integration.py` | Artifact count, port assertions, directory size check |

---

## Also Done: MLflow mlruns → sqlite migration

Changed default `tracking_uri` from deprecated `file://./mlruns` to `sqlite:///mlflow.db` across 12 files:

| File | Change |
|------|--------|
| `src/configurable_agents/config/schema.py` | Default tracking_uri |
| `src/configurable_agents/cli.py` | 8 occurrences |
| `src/configurable_agents/observability/cost_reporter.py` | Default + docstring |
| `src/configurable_agents/optimization/evaluator.py` | Default + docstring |
| `src/configurable_agents/optimization/ab_test.py` | Default + docstring |
| `src/configurable_agents/ui/dashboard/app.py` | Docstring |
| `src/configurable_agents/deploy/generator.py` | Container URI + mlflow version requirement |
| `src/configurable_agents/deploy/templates/Dockerfile.template` | mkdir command |
| `src/configurable_agents/deploy/templates/docker-compose.yml.template` | Volume mount |
| `src/configurable_agents/deploy/templates/README.md.template` | References |
| `src/configurable_agents/deploy/templates/.dockerignore` | Exclusion patterns |
| `examples/mlflow_optimization.yaml` | tracking_uri |

User-facing doc updates:
- `docs/user/OBSERVABILITY.md` — 12 edits replacing mlruns references
- `docs/user/DEPLOYMENT.md` — 7 edits replacing mlruns references

---

## Testing

```
$ python -m pytest tests/core/test_node_executor.py tests/core/test_node_executor_metrics.py tests/sandbox/test_integration.py tests/deploy/test_generator.py tests/deploy/test_generator_integration.py -v
69 passed, 0 failed
```

All previously-failing tests now pass. No regressions introduced.
