# BF-009: Remove Vestigial `--enable-profiling` CLI Flag

**Date**: 2026-02-14
**Status**: Complete
**Related**: CLI Verification, ADR-018 (MLflow 3.9 Migration)

---

## Overview

Removed the `--enable-profiling` flag from the CLI because it was non-functional (vestigial code). The flag was defined in the argument parser but never passed to `run_workflow()`, so it had no effect. Profiling is always captured via MLflow 3.9's `autolog()` feature.

---

## Problem Statement

The `--enable-profiling` flag appeared in CLI help and was accepted by the parser, but:

1. **Flag never used**: The flag value was never passed to `run_workflow()` or any other function
2. **Profiling always enabled**: MLflow 3.9's `autolog(log_traces=True)` captures all timing data automatically
3. **User confusion**: Flag suggested profiling could be disabled, but it cannot

---

## What Changed

### Source Code (2 files)

| File | Change |
|------|--------|
| `src/configurable_agents/cli.py` | Removed `--enable-profiling` flag from argument parser (lines 2148-2152). Removed backwards-compatibility comment (line 229). |
| `tests/observability/test_cli_commands.py` | Removed `TestEnableProfilingFlag` test class (18 lines). Added comment explaining flag removal. |

### Documentation (3 files)

| File | Change |
|------|--------|
| `docs/user/cli_guide.md` | Removed `--enable-profiling` from `run` command flags table. Updated example command. Updated `profile-report` note to clarify timing is auto-captured. |
| `docs/development/CLI_VERIFICATION_REPORT.md` | Created comprehensive CLI verification report documenting all 14 commands, 30+ flag variants, with BF-009 listed as FIXED. |
| `docs/development/bugs/BF-009-redundant-profiling-metrics.md` | Created bug report documenting redundant `node_*_duration_ms` metrics logged by custom profiler. Fix deferred to ADR-018 implementation. |

### CHANGELOG.md

Added BF-009 entry under "Fixed" section:
```
**BF-009: Remove vestigial --enable-profiling CLI flag** (2026-02-14)
```

---

## Evidence of Vestigial Nature

### Before: Flag Defined But Not Used
```python
# cli.py (lines 2148-2152) - REMOVED
run_parser.add_argument(
    "--enable-profiling",
    action="store_true",
    help="Enable performance profiling for this run (captures node timing data)",
)
```

### Before: Backwards-Compatibility Comment - REMOVED
```python
# cli.py (line 229) - REMOVED
# Note: --enable-profiling is accepted for backwards compatibility but profiling
# data is always captured via MLflow trace spans. Use profile-report to view it.
```

### After: Flag Removed
```bash
$ configurable-agents run --help
# No longer shows --enable-profiling option

$ configurable-agents run workflow.yaml --enable-profiling
# Error: unrecognized arguments: --enable-profiling
```

---

## Redundant Metrics Issue (Documented, Not Fixed)

The bug report also documents a related but separate issue:

**Custom profiler logs redundant `node_*_duration_ms` metrics to MLflow**

- `profiler.py` logs `node_{node_id}_duration_ms` via `mlflow.log_metric()`
- MLflow 3.9 `autolog()` already captures span timing via `start_time_ns`/`end_time_ns`
- `profile-report` command reads from traces, NOT from custom metrics
- Nothing in codebase reads the custom `node_*_duration_ms` metrics

**Impact**: Low - functional but wasteful (redundant data stored)

**Fix**: DEFERRED to ADR-018 implementation (MLflow 3.9 comprehensive migration)

---

## Testing

- **Manual verification**: `configurable-agents run --help` no longer shows flag
- **Existing tests**: Removed `TestEnableProfilingFlag` class (flag no longer exists)
- **Run command**: Works correctly without the flag
- **Profile reporting**: Still works - uses MLflow traces, not the removed flag

---

## Risk Assessment

**Risk**: None - removing dead code that had no effect

**User Impact**: Low - flag was non-functional, so removing it doesn't change behavior

**Breaking Change**: No - the flag never worked, so this is purely cleanup

---

## Related Issues

- **VF-002** (CL-003): Previously removed dead `CONFIGURABLE_AGENTS_PROFILING` env var code
- **ADR-018**: MLflow 3.9 migration - may address redundant metrics in future

---

## Verification Commands

```bash
# Verify flag is removed
configurable-agents run --help | grep -i "profiling"
# Should return nothing

# Verify run still works
configurable-agents run test_configs/01_basic_linear.yaml

# Verify profile-report still works
configurable-agents profile-report
```

---

## Files Changed

```
src/configurable_agents/cli.py                              |   8 --
tests/observability/test_cli_commands.py                   |  52 +----
docs/user/cli_guide.md                                    | 120 +++++---
docs/development/CLI_VERIFICATION_REPORT.md               | 240 ++++++++++
docs/development/bugs/BF-009-redundant-profiling-metrics.md | 120 +++++++
CHANGELOG.md                                              |  10 +
6 files changed, 467 insertions(+), 83 deletions(-)
```

---

## Commit

**Commit Hash**: `7b661a9`
**Branch**: `local_only_temp`
**Message**: `BF-009: Remove vestigial --enable-profiling flag`

---

*Bug identified during comprehensive CLI verification (2026-02-14)*
