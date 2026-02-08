# BF-004: Fix MLFlow Cost Summary and GenAI View Integration

**Date**: 2026-02-08
**Status**: Complete — verified on configs 02 and 12

---

## Overview

Fixed the MLFlow cost summary pipeline end-to-end: from trace querying through cost estimation to storage. Additionally migrated cost data storage from run-level APIs (invisible in GenAI view) to trace-level assessments (visible in GenAI experiment UI).

---

## Problems Found (4 issues)

### Issue 1: search_traces() location format
**Error**: `invalid literal for int() with base 10: 'mlflow-experiment:1'`
**Root Cause**: Code used `locations=[f"mlflow-experiment:{experiment.experiment_id}"]` but MLflow 3.9 expects raw experiment IDs: `locations=["1"]`
**File**: `mlflow_tracker.py:344-348`

### Issue 2: search_traces() return type
**Error**: `KeyError: 0` (logged as `Failed to get cost summary: 0`)
**Root Cause**: `search_traces()` returns pandas DataFrame by default. `traces[0]` accessed column "0" instead of row 0. Needed `return_type="list"` to get Trace objects.
**File**: `mlflow_tracker.py:344-348`

### Issue 3: Model name attribution
**Error**: `Cannot auto-detect provider for model: unknown`
**Root Cause**: Code only checked `ai.model.name` span attribute (OpenTelemetry convention). Gemini/LangChain spans don't set this — model name is in `invocation_params.model` and `metadata.ls_model_name`.
**File**: `mlflow_tracker.py:372`

### Issue 4: Token key mismatch
**Symptom**: `prompt_tokens: 0, completion_tokens: 0` despite tokens being tracked
**Root Cause**: Gemini spans use `input_tokens`/`output_tokens` in `mlflow.chat.tokenUsage`, but code expected OpenAI convention `prompt_tokens`/`completion_tokens`.
**Files**: `mlflow_tracker.py:378-379, 420-428, 514-516`

### Bonus: Cost data invisible in MLflow GenAI view
**Root Cause**: `log_workflow_summary()` used `mlflow.log_metrics()` and `mlflow.log_dict()` which attach to runs. GenAI experiments are trace-centric — runs are hidden. Need `mlflow.log_feedback()` to attach assessments to traces.

### Bonus: Race condition on feedback logging
**Root Cause**: Trace export is async. `log_feedback()` was called before trace was flushed to DB, causing `NOT NULL constraint failed: assessments.trace_id`.
**File**: `executor.py:324-328`

---

## Changes Made

| File | Lines | Change |
|------|-------|--------|
| `mlflow_tracker.py` | 344-349 | `locations=[experiment.experiment_id]` + `return_type="list"` |
| `mlflow_tracker.py` | 372-377 | Model name fallback chain (3 attribute keys) |
| `mlflow_tracker.py` | 378-379 | Token key fallback (`prompt_tokens` → `input_tokens`) |
| `mlflow_tracker.py` | 384-391 | Per-span `try/except ValueError` on cost estimation |
| `mlflow_tracker.py` | 420-428 | Same token key fallback in total_tokens sum |
| `mlflow_tracker.py` | 452-540 | Rewrote `log_workflow_summary()` to use `log_feedback()` |
| `mlflow_tracker.py` | 514-516 | Token key fallback in breakdown dict |
| `executor.py` | 324-328 | `mlflow.flush_trace_async_logging()` before cost query |

---

## Testing

### Config 02 (with_observability)
```
$ python -m configurable_agents.cli run test_configs/02_with_observability.yaml --input message="Hello"
+ Workflow executed successfully!
```
- No `Failed to get cost summary` errors
- Assessments verified on trace:
  - `cost_usd: 9e-06`
  - `total_tokens: 40`
  - `cost_breakdown: {input_tokens: 22, output_tokens: 18, google_cost_usd: 9e-06, google_tokens: 40, google_calls: 1}`

### Config 12 (full_featured)
```
$ python -m configurable_agents.cli run test_configs/12_full_featured.yaml --input "query=quantum computing" --input "depth=basic"
+ Workflow executed successfully!
```
- No MLFlow errors in output

---

## Where Cost Data Appears in MLflow GenAI View

| Assessment | Type | Where Visible |
|---|---|---|
| `cost_usd` | numeric | Traces tab column, Overview > Quality chart |
| `total_tokens` | numeric | Traces tab column, Overview > Quality chart |
| `cost_breakdown` | dict | Trace detail panel |

To view: `mlflow ui --backend-store-uri sqlite:///mlflow_test.db` → Experiment → GenAI view
