# Milestone Context: v1.2 Integration Testing & Critical Bug Fixes

**Generated:** 2026-02-05
**Type:** Test & Fix Milestone (not feature development)

## Problem Statement

After attempting to use the system, we discovered that the platform is essentially broken:

### Critical Issues Found

1. **CLI run command** - Completely broken (UnboundLocalError) - FIXED
2. **Chat UI** - Multi-turn conversations broken (history format wrong)
3. **Chat UI** - Download/Validate broken (same history issue)
4. **Dashboard - Workflows page** - Missing macros.html template
5. **Dashboard - Agents page** - Jinja2 underscore import error
6. **Dashboard - MLFlow page** - Returns 404
7. **Dashboard - Optimization** - MLFlow filesystem backend error

### Core Issue

**The system claims 1,018+ tests with 98%+ pass rate, but basic functionality is completely broken.**

This indicates:
- Tests are heavily mocked and don't test real functionality
- No integration tests for actual user workflows
- No end-to-end testing of UI components
- Tests pass but system doesn't work

## Milestone Goals

**Primary Goal:** Make the system actually work through comprehensive testing and bug fixes.

**Success Criteria:**
1. All CLI commands work without errors
2. All Dashboard pages load and function correctly
3. Chat UI works end-to-end (config generation, download, validate, multi-turn)
4. Workflows can run from CLI without crashes
5. Workflows can run from UI without crashes
6. Integration tests prevent regression

## Scope

### In Scope
- Test every component thoroughly
- Fix all discovered bugs
- Add integration tests for critical user workflows
- Ensure end-to-end functionality works

### Out of Scope
- New features (defer to v1.3+)
- Performance optimization (unless broken)
- Architectural refactoring (unless needed for fixes)

## Approach

**Phase-based testing and fixing:**
1. Test CLI commands comprehensively
2. Test Dashboard UI (all pages)
3. Test Chat UI (all features)
4. Test workflow execution (CLI and UI)
5. Test integrations (MLFlow, etc.)
6. Add integration tests for all fixed functionality

**Each phase:**
- Test thoroughly
- Document all failures
- Fix all failures
- Add integration tests
- Verify fixes

## User Expectation

> "I need an extensively tested, all things and cases covered system, that does not break when I run it."
> "Test everything and every component thoroughly."
> "From what I gave you, you can see, I can neither run flows from UI nor from cli."

This is a **quality milestone** - make it work before adding more features.
