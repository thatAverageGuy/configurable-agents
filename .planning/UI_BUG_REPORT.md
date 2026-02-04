# UI Bug Report

**Generated:** 2026-02-05
**Context:** After fixing Windows multiprocessing, systematic testing revealed multiple pre-existing bugs

## Critical Bugs (Block Core Functionality)

### 1. ✅ CLI `run` Command - FIXED
- **Status:** Fixed in commit d0e53b5
- **Issue:** UnboundLocalError: cannot access local variable 'Console'
- **Root Cause:** Line 205 checked `if RICH_AVAILABLE and Console:` before importing Console
- **Fix:** Changed to `if RICH_AVAILABLE:` only
- **Impact:** Users could not run any workflows

### 2. ❌ Chat UI - Conversation Follow-Up Broken
- **Error:** `ValueError: too many values to unpack (expected 2)`
- **Location:** `gradio_chat.py:167` in `_build_conversation_context`
- **Code:** `for i, (user_msg, asst_msg) in enumerate(history[-5:]):`
- **Root Cause:** Assumes Gradio history is `[(user, asst), ...]` but actual format is different
- **Impact:** Cannot have multi-turn conversations
- **Severity:** HIGH - Core chat functionality broken

### 3. ❌ Chat UI - Download/Validate Config Broken
- **Error:** `KeyError: 1` at lines 395 and 429
- **Location:** `gradio_chat.py` in `download_config` and `validate_config`
- **Code:** `last_message = history[-1][1] if history[-1][1] else None`
- **Root Cause:** Same issue as #2 - wrong history format assumption
- **Impact:** Cannot download or validate generated configs
- **Severity:** HIGH - Blocks config generation workflow

## High Priority Bugs (Block UI Pages)

### 4. ❌ Dashboard - Workflows Page Crashes
- **Error:** `jinja2.exceptions.TemplateNotFound: 'macros.html'`
- **Location:** `workflows_table.html:1`
- **Code:** `{% import "macros.html" as macros %}`
- **Root Cause:** macros.html doesn't exist in templates directory
- **Impact:** Cannot view workflows list
- **Fix Needed:** Either create macros.html or remove import

### 5. ❌ Dashboard - Agents Page Crashes
- **Error:** `jinja2.exceptions.TemplateAssertionError: names starting with an underline can not be imported`
- **Location:** `agents_table.html:1`
- **Code:** `{% from 'configurable_agents.ui.dashboard.routes.agents' import _time_ago, _parse_capabilities %}`
- **Root Cause:** Jinja2 forbids importing underscore-prefixed names
- **Impact:** Cannot view agents list
- **Fix Needed:** Rename functions without underscore prefix

### 6. ❌ Dashboard - MLFlow Page Returns 404
- **Error:** `{detail: Not found}` (web), no terminal error
- **Location:** MLFlow route
- **Root Cause:** Route not implemented or broken
- **Impact:** Cannot access MLFlow integration
- **Fix Needed:** Investigate route registration

## Medium Priority Bugs

### 7. ❌ Dashboard - Optimization Page MLFlow Error
- **Error:** `Failed to get comparison: [WinError 2] The system cannot find the file specified: '\\.\mlruns'`
- **Location:** MLFlow backend initialization
- **Root Cause:** Filesystem backend path issue on Windows
- **Impact:** Optimization features may not work
- **Fix Needed:** Configure MLFlow with proper database backend instead of filesystem

## Summary Statistics

- **Total Bugs Found:** 7
- **Fixed:** 1
- **Critical (Block Core):** 3 remaining
- **High Priority (Block UI):** 3 remaining
- **Medium Priority:** 1 remaining

## Testing Gaps Identified

These bugs reveal significant testing gaps:

1. **No integration tests** for Chat UI history handling
2. **No smoke tests** for dashboard page loads
3. **No end-to-end tests** for config generation workflow
4. **Tests likely mocked** - real functionality never verified

## Recommended Next Steps

1. ✅ **DONE:** Fix Windows multiprocessing (Quick tasks 001-008)
2. ✅ **DONE:** Fix CLI run command (Quick task 009)
3. 🔧 **TODO:** Fix Chat UI history handling (requires understanding actual Gradio format)
4. 🔧 **TODO:** Fix Dashboard templates (create/rename files)
5. 🔧 **TODO:** Add integration tests to prevent regression

## Related Quick Tasks

- Quick-001 to Quick-008: Windows multiprocessing fixes (complete)
- Quick-009: CLI run command fix (complete)
