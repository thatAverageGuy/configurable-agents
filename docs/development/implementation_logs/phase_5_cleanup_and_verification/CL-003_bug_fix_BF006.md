# BF-006: Migrate ChatLiteLLM from langchain-community to langchain-litellm

**Date**: 2026-02-09
**Status**: Complete

---

## Overview

Migrated `ChatLiteLLM` from the deprecated `langchain-community` package to the standalone `langchain-litellm` package. `ChatLiteLLM` was deprecated in `langchain-community` 0.3.24 with a `LangChainDeprecationWarning` directing users to the new package.

This resolves R-004 from [CL-003 Test Findings](CL-003_TEST_FINDINGS.md).

---

## What Changed

### Source Code (2 files)

| File | Change |
|------|--------|
| `src/configurable_agents/llm/litellm_provider.py` | Import: `from langchain_community.chat_models import ChatLiteLLM` → `from langchain_litellm import ChatLiteLLM`. Updated docstring and error message. |
| `src/configurable_agents/llm/provider.py` | Import: `from langchain_community.chat_models import ChatLiteLLM` → `from langchain_litellm import ChatLiteLLM` |

### Dependencies (1 file)

| File | Change |
|------|--------|
| `pyproject.toml` | Added `langchain-litellm>=0.2.0` to dependencies. Kept `langchain-community` (still used by `tools/serper.py`). |

### Tests (2 files, 11 mock paths)

| File | Change |
|------|--------|
| `tests/llm/test_litellm_provider.py` | 8 `@patch("langchain_community.chat_models.ChatLiteLLM")` → `@patch("langchain_litellm.ChatLiteLLM")` |
| `tests/llm/test_provider.py` | 3 `@patch("langchain_community.chat_models.ChatLiteLLM")` → `@patch("langchain_litellm.ChatLiteLLM")` |

### Pre-existing Test Fixes (3 files, 4 tests)

Also fixed 4 pre-existing test failures unrelated to BF-006, caused by the BF-004 `log_workflow_summary` rewrite and mlruns→sqlite migration:

| Test | Root Cause | Fix |
|------|-----------|-----|
| `test_schema.py::test_mlflow_config_defaults` | Default `tracking_uri` changed to `sqlite:///mlflow.db` but test expected `file://./mlruns` | Updated expected value |
| `test_mlflow_integration.py::test_log_summary_creates_metrics` | `log_workflow_summary` now uses `mlflow.log_feedback()` not `mlflow.log_metrics()`, and requires `trace_id` | Updated to mock `log_feedback`, added `trace_id` |
| `test_mlflow_tracker.py::test_log_summary_logs_metrics` | Same as above | Same fix |
| `test_mlflow_tracker.py::test_log_summary_logs_artifact` | Now uses `log_feedback` with `cost_breakdown` instead of `log_dict` | Updated assertions |

---

## Testing

- **48/48** LiteLLM + provider tests pass (direct test of BF-006 changes)
- **4/4** previously-failing tests now pass (pre-existing fixes)
- **1410 passed, 0 failed, 37 skipped** (full suite excluding UI — UI tests have a pre-existing `_time_ago` import error)

---

## Risk Assessment

**Risk**: Very low — pure import path change, API is identical between old and new package.

**Package**: `langchain-litellm` v0.4.0 installed (latest). Same `ChatLiteLLM` class, just relocated.

**Backward compatibility**: `langchain-community` is retained as a dependency for `tools/serper.py` (`GoogleSerperAPIWrapper`).
