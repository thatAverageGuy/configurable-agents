# Version Audit Report

**Date**: 2026-02-06
**Scope**: Audit version number consistency across project
**Type**: LEVEL 0 (audit only, no changes made)

---

## Version Status Summary

**⚠️ VERSION INCONSISTENCY DETECTED**

**Declared Version**: 1.0.0 (in documentation and git tags)
**Code Version**: 0.1.0-dev (in pyproject.toml and __init__.py)
**Status**: Code needs update to match declared version

---

## Version Declarations by Location

### Git Tags
```bash
$ git tag -l
v1.0
```
**Declared**: v1.0 ✅

### pyproject.toml
```toml
[project]
name = "configurable-agents"
version = "0.1.0-dev"  ⚠️ MISMATCH
```
**Current**: 0.1.0-dev

### src/configurable_agents/__init__.py
```python
__version__ = "0.1.0-dev"  ⚠️ MISMATCH
```
**Current**: 0.1.0-dev

### CHANGELOG.md
```markdown
## [1.0.0] - 2026-02-04
...
Current version: **1.0.0** (production release)
```
**Declared**: 1.0.0 ✅

### README.md
```markdown
[![Version](https://img.shields.io/badge/version-1.0.0-blue)]
```
**Declared**: 1.0.0 ✅

### docs/TASKS.md
```markdown
**Version**: v1.0 Shipped (2026-02-04)
```
**Declared**: v1.0 ✅

---

## Version Timeline Alignment

### What Should Be

Based on actual development history and milestone completion:

| Milestone | Version | Date | Status | Code Version |
|-----------|---------|------|--------|-------------|
| v0.1 Alpha | 0.1.0-dev | 2026-01-24 to 2026-02-02 | ✅ Complete | 0.1.0-dev ✅ |
| v1.0 Foundation | 1.0.0 | 2026-02-03 to 2026-02-04 | ✅ Shipped | 0.1.0-dev ❌ |
| v1.1 Core UX Polish | 1.1.0 | 2026-02-04 to 2026-02-05 | ✅ Shipped | 0.1.0-dev ❌ |
| v1.2 Integration Testing | 1.2.0 | 2026-02-05 to present | 🔄 In Progress | 0.1.0-dev ❌ |

---

## Inconsistencies Found

### 1. Code Version vs Documentation
**Severity**: HIGH

**Issue**: Code still reports 0.1.0-dev, but documentation claims 1.0.0 (production release)

**Locations**:
- pyproject.toml: `version = "0.1.0-dev"` (should be `1.0.0`)
- src/__init__.py: `__version__ = "0.1.0-dev"` (should be `1.0.0`)

**Impact**:
- Users installing from source will see version 0.1.0-dev
- Confusion about actual release version
- Package managers (pip) will show wrong version

**Recommendation**: Update to `1.0.0` or `1.2.0` (if including latest work)

---

### 2. Git Tag Coverage
**Severity**: MEDIUM

**Current Tags**:
- ✅ v1.0 exists

**Missing Tags** (based on shipped milestones):
- ❌ v0.1.0 (for alpha release)
- ❌ v1.1.0 (for Core UX Polish)

**Impact**:
- Cannot checkout specific milestone versions
- Cannot easily rollback to v1.1.0

**Recommendation**: Consider creating tags for major milestones

---

## Recommendations

### For Immediate Fix

**Action Required**: Update code version to match current milestone

**Files to Update**:
1. `pyproject.toml`: Change `version = "0.1.0-dev"` → `version = "1.2.0"`
2. `src/configurable_agents/__init__.py`: Change `__version__ = "0.1.0-dev"` → `__version__ = "1.2.0"`

**Rationale**:
- v1.0 shipped 2026-02-04
- v1.1 shipped 2026-02-05
- v1.2 in progress (Phase 7-11)
- Current code represents v1.2 work, not v0.1

### For Future Maintenance

**Best Practices**:
1. **Sync versions**: Update pyproject.toml and __init__.py with each release
2. **Tag releases**: Create git tag for each shipped version (v1.0, v1.1, v1.2, etc.)
3. **Update CHANGELOG.md**: Move unreleased entries to new version section
4. **Documentation**: Keep version numbers consistent across all docs

**Version Bump Process**:
1. Update pyproject.toml
2. Update __init__.py
3. Commit changes
4. Create git tag: `git tag -a v1.X.0 -m "Release v1.X.0"`
5. Push tags: `git push origin v1.X.0`

---

## Version History (Actual vs Declared)

| Milestone | Actual Code Version | Git Tag | Documentation | Status |
|-----------|-------------------|----------|---------------|--------|
| v0.1 Alpha | 0.1.0-dev | None | changelog_old.md | ✅ Complete |
| v1.0 | 0.1.0-dev | v1.0 | CHANGELOG.md | ⚠️ Version mismatch |
| v1.1 | 0.1.0-dev | None | CHANGELOG.md | ⚠️ Version mismatch |
| v1.2 | 0.1.0-dev | None | In progress | ⚠️ Version mismatch |

---

## Semantic Versioning Compliance

**Current state**: NOT COMPLIANT

**Issue**: Semantic versioning requires:
1. Version declared in code (pyproject.toml)
2. Git tag for release
3. CHANGELOG entries for each version

**Current compliance**:
- ✅ CHANGELOG entries exist
- ❌ Code version doesn't match release version
- ⚠️ Only v1.0 tag exists (missing v0.1, v1.1)

---

## Related Documents

- `tasks_old.md` - Complete task history with dates
- `changelog_old.md` - v0.1 changelog
- `CHANGELOG.md` - v1.0+ changelog
- `docs/TASKS.md` - Requirements with version info
- `.planning/milestones/v1.0-MILESTONE-AUDIT.md` - v1.0 verification

---

**Audit Status**: ⚠️ COMPLETE
**Issues Found**: 1 critical (version mismatch)
**Recommendations**: Update code version or add version tags

*This audit documents version inconsistencies as of 2026-02-06. No changes were made (LEVEL 0 audit only).*
