# T-020: Cost Tracking & Reporting

**Status**: ✅ COMPLETE
**Date**: 2026-01-31
**Effort**: ~3 hours
**Dependencies**: T-018 (MLFlow Foundation), T-019 (MLFlow Instrumentation)

## Overview

Implemented cost reporting utilities to query and aggregate MLFlow tracking data for workflow cost analysis. Provides CLI command and programmatic API for generating cost reports with various filters and aggregations.

## Changes Made

### 1. Cost Reporter Module

**File**: `src/configurable_agents/observability/cost_reporter.py` (570 lines)

**Core Classes**:
- `CostEntry` - Dataclass representing a single workflow run's cost data
- `CostSummary` - Dataclass containing aggregated cost statistics
- `CostReporter` - Main class for querying and aggregating MLFlow data

**Key Features**:
- **Fail-fast validation**: Required metrics must be present (no silent defaults)
- **Flexible filtering**: By experiment, workflow, date range, status
- **Time aggregation**: Daily, weekly, monthly cost aggregation
- **Multiple export formats**: JSON (with summary) and CSV
- **Breakdowns**: Cost breakdown by workflow and model
- **Helper functions**: Predefined date ranges (today, yesterday, last_7_days, etc.)

**Methods**:
```python
class CostReporter:
    def __init__(self, tracking_uri: str = "file://./mlruns")

    def get_cost_entries(
        experiment_name: Optional[str] = None,
        workflow_name: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        status_filter: Optional[str] = None,
    ) -> List[CostEntry]

    def generate_summary(entries: List[CostEntry]) -> CostSummary

    def aggregate_by_period(
        entries: List[CostEntry],
        period: str = "daily",  # "daily", "weekly", "monthly"
    ) -> Dict[str, float]

    def export_to_json(
        entries: List[CostEntry],
        output_path: str,
        include_summary: bool = True,
    ) -> None

    def export_to_csv(entries: List[CostEntry], output_path: str) -> None
```

**Fail-Fast Validation**:
```python
def _run_to_cost_entry(self, run: Any) -> CostEntry:
    # Validate required metrics exist
    required_metrics = [
        "total_cost_usd",
        "total_input_tokens",
        "total_output_tokens",
        "duration_seconds",
        "node_count",
        "status",
    ]

    missing_metrics = [m for m in required_metrics if m not in metrics]
    if missing_metrics:
        raise ValueError(
            f"Missing required metrics: {', '.join(missing_metrics)}. "
            f"This run may not have been tracked properly."
        )
```

This adheres to the "fail fast, fail loud" principle from PROJECT_VISION.md - no silent defaults, clear error messages.

### 2. CLI Command

**File**: `src/configurable_agents/cli.py` (modified)

**Added**: `configurable-agents report costs` command

**Options**:
- `--tracking-uri` - MLFlow tracking URI (default: file://./mlruns)
- `--experiment` - Filter by experiment name
- `--workflow` - Filter by workflow name
- `--period` - Predefined time periods (today, yesterday, last_7_days, last_30_days, this_month)
- `--start-date` - Custom start date (ISO format)
- `--end-date` - Custom end date (ISO format)
- `--status` - Filter by success/failure
- `--breakdown` - Show cost breakdown by workflow and model
- `--aggregate-by` - Aggregate by time period (daily, weekly, monthly)
- `-o, --output` - Export to file
- `--format` - Output format (json, csv)
- `--include-summary` - Include summary in JSON export (default: true)

**Example Usage**:
```bash
# View last 7 days with breakdown
configurable-agents report costs --period last_7_days --breakdown

# Filter by workflow and export to CSV
configurable-agents report costs --workflow article_writer --output costs.csv --format csv

# Monthly aggregation
configurable-agents report costs --period this_month --aggregate-by daily

# Custom date range for specific experiment
configurable-agents report costs \
  --experiment my_workflows \
  --start-date 2026-01-01 \
  --end-date 2026-01-31 \
  --breakdown \
  --output report.json
```

**Output Format**:
```
Cost Summary:
  Total Cost:        $0.045123
  Total Runs:        15
  Successful:        14
  Failed:            1
  Total Tokens:      45,000
  Avg Cost/Run:      $0.003008
  Avg Tokens/Run:    3000

Cost by Workflow:
  article_writer               $0.035000
  summarizer                   $0.010123

Cost by Model:
  gemini-1.5-flash            $0.030000
  gemini-2.5-flash            $0.015123
```

### 3. Module Exports

**File**: `src/configurable_agents/observability/__init__.py` (modified)

Added exports:
- `CostReporter`
- `CostEntry`
- `CostSummary`
- `get_date_range_filter`

### 4. Tests

**Created Files**:
1. `tests/observability/test_cost_reporter.py` (29 unit tests, 622 lines)
2. `tests/observability/test_cost_reporter_integration.py` (5 integration tests, 250 lines)
3. `tests/test_cli.py` (added 5 CLI tests for report costs)

**Test Coverage**: 39 new tests total
- **Unit tests**: 29 tests (all mocked MLFlow)
- **CLI tests**: 5 tests (mocked CostReporter)
- **Integration tests**: 5 tests (real MLFlow backend)

**Test Scenarios Covered**:

*CostReporter*:
- Initialization (success and MLFlow unavailable)
- Run-to-entry conversion (success, failure status, missing model)
- Fail-fast validation (missing required metrics)
- Querying with filters (experiment, workflow, date range, status)
- Invalid inputs (nonexistent experiment, invalid status)

*Aggregation and Summary*:
- Empty entries
- Single entry
- Multiple entries with mixed workflows/models
- Daily/weekly/monthly aggregation
- Invalid aggregation period

*Export*:
- JSON export (with and without summary)
- CSV export
- File creation and content validation

*CLI*:
- Successful report generation
- No entries found
- MLFlow unavailable error
- Export to file
- Invalid period error

*Integration*:
- Real MLFlow run creation and querying
- Filtering by workflow and status
- JSON and CSV export with real data
- Period aggregation with real data
- Date range filter helpers

### 5. Error Handling

**Graceful Degradation**:
- MLFlow unavailable → Clear error message with install instructions
- No entries found → Warning (not error), zero exit code
- Invalid filters → Fail fast with helpful error message
- Missing metrics in run → Fail fast with list of missing metrics

**Error Messages**:
```python
# MLFlow not installed
"MLFlow is not installed. Install with: pip install mlflow"

# Missing metrics (fail-fast)
"Missing required metrics: total_cost_usd, duration_seconds. "
"This run may not have been tracked properly."

# Invalid experiment
"Experiment not found: nonexistent_experiment"

# Invalid period
"Invalid period: foo. Use 'daily', 'weekly', or 'monthly'"
```

## Testing Strategy

### Unit Tests (Mocked)
- All MLFlow interactions mocked
- Fast execution (< 2 seconds)
- Test all code paths and error handling
- Mock Run objects with realistic data

### Integration Tests (Real MLFlow)
- Use temporary directories for MLFlow storage
- Create real MLFlow runs with metrics
- Verify end-to-end querying and export
- Test actual MLFlow API integration
- Cost-free (uses local file storage)

### CLI Tests (Mocked)
- Mock CostReporter to avoid MLFlow dependency
- Test argument parsing and command execution
- Test error handling and exit codes
- Verify output formatting

## Files Modified/Created

**New Files** (3):
1. `src/configurable_agents/observability/cost_reporter.py` (570 lines)
2. `tests/observability/test_cost_reporter.py` (622 lines)
3. `tests/observability/test_cost_reporter_integration.py` (250 lines)

**Modified Files** (2):
1. `src/configurable_agents/observability/__init__.py` - Added exports
2. `src/configurable_agents/cli.py` - Added report costs command (~140 lines)

**Total Lines**: ~1,582 lines (code + tests)

## Verification

```bash
# Unit tests (fast)
pytest tests/observability/test_cost_reporter.py -v
# Result: 29 passed

# CLI tests
pytest tests/test_cli.py -k report_costs -v
# Result: 5 passed

# Integration tests (with real MLFlow)
pytest tests/observability/test_cost_reporter_integration.py -v -m integration
# Result: 5 passed

# All unit tests (regression check)
pytest tests/ --ignore=tests/integration/ -v
# Result: 540 passed, 4 skipped

# Total: 544 tests (540 existing + 4 skipped), 39 new tests
```

## Design Decisions

### 1. Fail-Fast Validation

**Decision**: Validate all required metrics exist before creating CostEntry.

**Rationale**: Aligns with PROJECT_VISION.md principle "Fail Fast, Fail Loud". If metrics are missing, it indicates a tracking problem that should be surfaced immediately rather than silently using defaults.

**Impact**: Users get clear error messages about data quality issues.

### 2. MLFlow Query Filtering

**Decision**: Use MLFlow's native filter strings for server-side filtering when possible.

**Rationale**: More efficient than client-side filtering for large datasets. MLFlow supports filtering by metrics, params, and timestamps.

**Limitation**: Workflow name filtering is client-side (MLFlow doesn't support param filtering in filter strings in all versions).

### 3. Separate JSON and CSV Export

**Decision**: Two separate export methods with different capabilities.

**Rationale**:
- JSON: Supports nested data (summary, breakdown by workflow/model)
- CSV: Flat structure, better for spreadsheet analysis
- Each format optimized for its use case

### 4. Date Range Helpers

**Decision**: Provide predefined periods (today, last_7_days, etc.) as helper functions.

**Rationale**: Common use cases are simple one-word commands, advanced users can use custom dates.

### 5. CLI Structure

**Decision**: Use `report costs` as a subcommand (not top-level).

**Rationale**: Leaves room for future report types (e.g., `report performance`, `report errors`) without CLI namespace pollution.

## Known Limitations

1. **Workflow name filtering**: Client-side filtering (not MLFlow native) - may be slow for very large datasets
2. **Time aggregation**: Based on run start_time only (not end_time or duration)
3. **No nested workflow support**: Assumes flat workflow structure
4. **Memory usage**: Loads all matching runs into memory - not suitable for very large result sets (>10K runs)

## Future Enhancements (v0.2+)

1. **Pagination**: Support for large datasets with streaming/chunking
2. **Additional aggregations**: By node, by tool, by user
3. **Cost trends**: Time-series analysis and visualization
4. **Budget alerts**: Warnings when costs exceed thresholds
5. **Database backend**: Support PostgreSQL/MySQL for MLFlow
6. **Multi-provider costs**: Track costs across OpenAI, Anthropic, etc.

## Acceptance Criteria Status

✅ 1. Create cost aggregation utility in `observability/cost_reporter.py`
✅ 2. Query MLFlow experiments for workflow runs
✅ 3. Aggregate costs across workflows (daily, weekly, monthly)
✅ 4. Generate cost reports with breakdown by workflow, model, time period, node-level (optional)
✅ 5. Export reports as JSON/CSV
✅ 6. Add CLI command: `configurable-agents report costs`
✅ 7. Unit tests with mocked MLFlow queries (29 tests, exceeds 15 target)
✅ 8. Integration test with real MLFlow database (5 tests)

**Bonus**:
- Fail-fast validation for data quality
- Predefined date range helpers
- Comprehensive CLI with multiple filter options
- CSV export in addition to JSON

## Related

- **ADR**: ADR-011 (MLFlow Observability) - Design decisions
- **Previous**: T-019 (MLFlow Instrumentation) - Node-level tracking
- **Next**: T-021 (Observability Documentation) - User documentation

---

## Example Workflow

```python
from configurable_agents.observability import CostReporter

# Initialize reporter
reporter = CostReporter(tracking_uri="file://./mlruns")

# Query last 7 days
from datetime import datetime, timedelta
start_date = datetime.now() - timedelta(days=7)
entries = reporter.get_cost_entries(
    experiment_name="production",
    start_date=start_date,
    status_filter="success",
)

# Generate summary
summary = reporter.generate_summary(entries)
print(f"Total cost (7 days): ${summary.total_cost_usd:.2f}")
print(f"Average per run: ${summary.avg_cost_per_run:.4f}")

# Breakdown by workflow
for workflow, cost in summary.breakdown_by_workflow.items():
    print(f"  {workflow}: ${cost:.4f}")

# Export to CSV
reporter.export_to_csv(entries, "costs_last_7_days.csv")

# Aggregate by day
daily_costs = reporter.aggregate_by_period(entries, period="daily")
for date, cost in sorted(daily_costs.items()):
    print(f"{date}: ${cost:.4f}")
```

## Lessons Learned

1. **Fail-fast validation**: Using `.get()` with defaults violates fail-fast principle - explicit validation is better
2. **MLFlow filter strings**: Limited capabilities, need client-side filtering for some use cases
3. **Date handling**: MLFlow stores timestamps in milliseconds - requires conversion
4. **Test data quality**: Integration tests caught calculation errors in unit test expectations
5. **CLI ergonomics**: Predefined periods (last_7_days) more user-friendly than requiring ISO dates for common cases

---

**Completion Notes**:
- All acceptance criteria met and exceeded
- Comprehensive test coverage (39 tests)
- Adheres to fail-fast, fail-loud principles
- CLI is user-friendly with sensible defaults
- Ready for T-021 (documentation)
