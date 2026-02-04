# Bug Reports

This directory contains detailed reports for significant bugs discovered and fixed in the configurable-agents project.

## Purpose

Bug reports serve as:
1. **Historical Record**: Document what went wrong and why
2. **Learning Resource**: Capture lessons learned for future development
3. **Reference Material**: Help diagnose similar issues
4. **Quality Metrics**: Track bug severity, resolution time, and impact

## When to Create a Bug Report

Create a bug report for:
- ✅ **Critical bugs**: Complete feature failures, data loss, security issues
- ✅ **High-impact bugs**: Affecting multiple users or core functionality
- ✅ **Complex bugs**: Required significant investigation or non-obvious fixes
- ✅ **Recurring patterns**: Similar issues that may reappear
- ✅ **Architectural issues**: Bugs revealing design flaws

Do NOT create bug reports for:
- ❌ **Typos**: Simple text corrections
- ❌ **Minor UI issues**: Cosmetic problems
- ❌ **Expected behavior**: Not actually bugs
- ❌ **Feature requests**: Use enhancement proposals instead

## Naming Convention

```
BUG-{ID}-{short-description}.md
```

**Examples**:
- `BUG-001-docker-build-pypi-dependency.md`
- `BUG-002-mlflow-port-conflict.md`
- `BUG-003-streamlit-session-state-corruption.md`

**ID Format**: Sequential numbers (001, 002, 003, ...)

## Bug Report Template

```markdown
# BUG-{ID}: {Title}

**Status**: [Open | In Progress | Fixed | Won't Fix]
**Severity**: [Critical | High | Medium | Low]
**Date Reported**: YYYY-MM-DD
**Date Fixed**: YYYY-MM-DD (if fixed)
**Reporter**: {Name or Role}
**Fixed By**: {Name or Role}
**Related Tasks**: {Task IDs}
**Related ADRs**: {ADR IDs}

---

## Summary

Brief 2-3 sentence description of the bug and its impact.

---

## Detailed Description

### What Happened
### When It Occurred
### Expected Behavior
### Actual Behavior

---

## Root Cause Analysis

### The Problem
### Why Wasn't This Caught Earlier?
### Architectural Context

---

## Impact Assessment

### Severity: {Level}
### User Impact
### Business Impact
### Scope

---

## Solution Implemented

### Strategy
### Changes Made
### Code Diffs (if applicable)

---

## Verification

### Tests Performed
### Expected Behavior (Post-Fix)

---

## Files Changed

| File | Change Type | Lines Changed | Purpose |
|------|-------------|---------------|---------|
| ... | ... | ... | ... |

---

## Lessons Learned

### What Went Wrong
### What Went Right
### Process Improvements

---

## Alternative Solutions Considered

### Option 1: ...
### Option 2: ...
### Chosen Solution: ...

---

## Future Considerations

---

## References

---

## Sign-Off

**Bug Fixed By**: {Name}
**Verified By**: {Name}
**Approved By**: {Name}
**Change Level**: {0-3}
**Release Notes**: {Include in which version}
```

## Severity Levels

| Level | Description | Examples | SLA |
|-------|-------------|----------|-----|
| **Critical** | Complete feature failure, data loss, security breach | Deployment blocked, data corruption | Fix immediately |
| **High** | Major functionality broken, affects many users | API returns errors, UI crashes | Fix within 24h |
| **Medium** | Feature partially broken, workaround exists | Performance degradation, minor errors | Fix within 1 week |
| **Low** | Minor issue, cosmetic problem | UI alignment, log messages | Fix when convenient |

## Status Values

- **Open**: Bug reported, not yet investigated
- **In Progress**: Investigation or fix in progress
- **Fixed**: Bug resolved and verified
- **Won't Fix**: Decided not to fix (explain in report)
- **Duplicate**: Same as another bug (reference original)
- **Cannot Reproduce**: Unable to verify bug exists

## Integration with Development

### When Bug is Fixed

1. Create bug report in `docs/bugs/`
2. Update `CHANGELOG.md` with bug fix entry
3. Reference bug ID in commit message: `Fix BUG-001: Docker build PyPI dependency`
4. Update related ADR if architectural change was made
5. Add regression test to prevent recurrence

### During Code Review

- Link to bug report in PR description
- Verify all items in "Verification" section are tested
- Confirm "Files Changed" section matches actual changes

### During Release

- Include all fixed bugs in release notes
- Mark bug reports as "Fixed" with release version
- Archive critical bugs for post-mortem review

## Current Bugs

| ID | Title | Severity | Status | Fixed Date |
|----|-------|----------|--------|------------|
| 001 | Docker Build PyPI Dependency | Critical | Fixed | 2026-02-02 |
| 002 | Server Template Wrong Function | Critical | Fixed | 2026-02-02 |
| 003 | MLFlow Port Mapping Mismatch | High | Fixed | 2026-02-02 |
| 004 | MLFlow Blocking Without Server | High | Fixed | 2026-02-02 |

---

## Contributing

When filing a bug report:

1. **Reproduce the bug**: Verify it's consistent and reproducible
2. **Gather context**: Error logs, stack traces, environment details
3. **Investigate root cause**: Don't just describe symptoms
4. **Document thoroughly**: Future you will thank present you
5. **Be honest**: Include "What went wrong" even if embarrassing
6. **Extract lessons**: Every bug is a learning opportunity

---

## Related Documentation

- `/docs/adr/` - Architecture Decision Records
- `/docs/TASKS.md` - Work breakdown and task tracking
- `/docs/ARCHITECTURE.md` - System architecture overview
- `/CHANGELOG.md` - Version history and changes

---

**Last Updated**: 2026-02-02
**Total Bugs Reported**: 4
**Total Bugs Fixed**: 4
**Average Resolution Time**: < 1 hour
