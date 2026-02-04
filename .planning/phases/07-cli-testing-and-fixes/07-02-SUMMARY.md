---
phase: 07-cli-testing-and-fixes
plan: 02
subsystem: testing
tags: [cli, validation, subprocess-tests, integration-tests, error-messages]

# Dependency graph
requires:
  - phase: 02-agent-infrastructure
    provides: config schema and validation framework
  - phase: 03-interfaces-and-triggers
    provides: CLI interface structure
provides:
  - Subprocess-based integration tests for CLI validate command
  - Improved validation error messages with actionable guidance
  - Cross-platform compatibility tests for path handling
affects: [07-03, 07-04, 07-05]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Subprocess-based CLI testing for real end-to-end validation
    - Error message pattern: error description + specific fix guidance

key-files:
  created:
    - tests/cli/test_cli_validate_integration.py
  modified:
    - src/configurable_agents/cli.py

key-decisions:
  - "Use subprocess.run([sys.executable, '-m', 'configurable_agents', 'validate', ...]) for true CLI invocation testing"
  - "Error messages now provide specific guidance based on error type (YAML syntax, schema, missing file)"

patterns-established:
  - "Integration tests use subprocess to test actual CLI entry point, catching import errors and entry point bugs"
  - "Validation error messages follow: Clear error description + Specific fix guidance + Actionable next steps"

# Metrics
duration: 14min
completed: 2026-02-05
---

# Phase 7 Plan 2: CLI Validate Command Integration Testing Summary

**Subprocess-based integration tests for validate command with improved error messages providing actionable guidance**

## Performance

- **Duration:** 14 min
- **Started:** 2026-02-04T20:21:39Z
- **Completed:** 2026-02-05T20:36:05Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Created comprehensive subprocess-based integration tests for CLI validate command (16 tests)
- Improved validation error messages with specific, actionable guidance based on error type
- Verified cross-platform compatibility for path handling (spaces, Windows separators)
- All 23 validate tests pass (7 unit + 16 integration)

## Task Commits

Each task was committed atomically:

1. **Task 1: Create subprocess integration test file for validate command** - `d2e3d0c` (test)
2. **Task 1 fix: Fix test configs to match schema requirements** - `ca66545` (fix)
3. **Task 2: Improve validation error messages with actionable guidance** - `a71ad15` (feat)

## Files Created/Modified

- `tests/cli/test_cli_validate_integration.py` - New subprocess-based integration tests with 6 test classes covering help, errors, valid configs, invalid configs, cross-platform paths, and error message quality
- `src/configurable_agents/cli.py` - Enhanced cmd_validate function with specific error guidance based on error type

## Test Coverage

### Integration Tests (tests/cli/test_cli_validate_integration.py)
- TestCLIValidateHelp (2 tests): Help output, verbose option
- TestCLIValidateErrors (3 tests): Missing file, invalid YAML, empty file
- TestCLIValidateValidConfigs (3 tests): Minimal valid, complete valid, verbose output
- TestCLIValidateInvalidConfigs (4 tests): Missing required field, missing flow name, invalid node reference, cyclic edges
- TestCLIValidateCrossPlatform (2 tests): Path with spaces, Windows path separators
- TestCLIValidateErrorMessageQuality (2 tests): Field names in errors, fix suggestions

### Unit Tests (tests/test_cli.py - existing)
- 7 existing unit tests for cmd_validate function

**Total: 23 tests for validate command (7 unit + 16 integration)**

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

**Issue 1: Test config format mismatch**
- **Problem:** Initial tests used list format for state.fields, but schema requires dict format
- **Resolution:** Fixed all test configs to use dict format with field names as keys
- **Impact:** All 16 integration tests now pass

**Issue 2: Node outputs must reference state fields**
- **Problem:** Validator requires all node outputs to be defined in state.fields
- **Resolution:** Added missing 'result' field to all test configs
- **Impact:** Tests now correctly validate cross-reference validation

## Error Message Improvements

### Before:
```
x Config file not found: {path}
```

### After:
```
x Config file not found: {path}
i Check that the file path is correct and the file exists
i Example: configurable-agents validate workflow.yaml
```

### YAML Syntax Errors:
```
x Failed to load config: {error}
i Fix: Check YAML syntax (indentation, colons, quotes)
i      Use a YAML validator: https://www.yamllint.com/
```

### Validation Errors (from validator.py - already good):
```
x Config validation failed: Edge 0: 'to' references unknown node 'nonexistent_node'

Context: Edge: START -> nonexistent_node

Suggestion: Valid nodes: ['END', 'START', 'node1']
```

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Integration test pattern established for subprocess-based CLI testing
- Error message improvement pattern can be applied to other CLI commands (run, deploy, etc.)
- Cross-platform path handling verified for Windows
- Ready to proceed with 07-03 (CLI dashboard command testing)
