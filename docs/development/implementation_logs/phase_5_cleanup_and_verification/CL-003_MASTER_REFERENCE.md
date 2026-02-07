# CL-003: Master Reference Document

**Purpose**: Comprehensive reference for cleanup and recovery process
**Date Created**: 2026-02-07
**Status**: Active working document

---

## Part 1: Project Vision (As Explained by User)

### Original v0.1 Vision

**Core Concept**: Config-driven dynamic agent execution
- No predefined flows or structure in code
- Define workflow in config (YAML/JSON parsed via Pydantic)
- Run and get output

**Persistence Model**:
- Workflows can be persisted as detached Docker containers
- Fire once, reuse any number of times via API calls
- Define workflow → Deploy to container → Reuse via API

**Interaction Options**:
- CLI
- Python API
- UI (Streamlit for v0.1)

**Observability & Cost Control**:
- MLFlow for monitoring and observability (core feature)
- Fail-fast to avoid costs
- Must be runnable locally

**DSPy Decision**:
- Originally planned for prompt optimization
- Cancelled after discovering MLFlow 3.9 has optimization features
- May reconsider if MLFlow optimization proves insufficient

**MLFlow Evolution**:
- Started with MLFlow 2.x implementation
- Discovered MLFlow 3.9 had excellent GenAI features
- Migrated entire codebase to MLFlow 3.9
- This migration was completed before "Release v0.1"

**v0.1 State** (at f0a4f96):
- System was functional
- Could paste config into Streamlit UI → execute → get output
- Could deploy config as standalone Docker → reuse via API
- Manually tested with bugs fixed
- **Problem**: Full MLFlow UI shipped with each Docker (~1.6GB per container)

---

### Post-v0.1 Vision (What Was Intended)

**Goal**: Make system realistically usable in real-world settings

**Runtime Enhancements**:
| Feature | Purpose |
|---------|---------|
| Branched/conditional flows | Real-world logic |
| Loops and retries | Error handling, iteration |
| Multi-LLM support | Provider flexibility |
| More tools | Extended capabilities |
| Arbitrary code execution | Dynamic behavior |
| Long-term memory | Context persistence |
| Deployment efficiency | Reduce container size |
| Enterprise hooks | Future extensibility |

**Dashboard UI** (Optional - can run as sidecar or local):
| Component | Purpose |
|-----------|---------|
| Chat interface | Generate valid configs via prompted conversation |
| Config execution | Execute directly from chat |
| Config deployment | Deploy to Docker from chat |
| MLFlow UI (embedded) | Observability within dashboard |
| Workflow registry | Track deployed workflows |
| Discovery/registration | Bidirectional - dashboard ↔ deployed containers |
| Execution histories | Track runs |

**Architecture Clarification from User**:
> "The system does WORKFLOWS. A well-designed workflow could be called an Agent, but they are the same thing. I don't know why the autonomous agent made Agents and Workflows as two separate entities - this is confusing."

**Deployment Architecture Change**:
- Dashboard is OPTIONAL (sidecar container or local)
- Core functionality (run, deploy) still works via CLI or Python API
- Only tracing/observability shipped with deployed containers (NOT full MLFlow)
- Deployed containers send MLFlow data to hosted/sidecar MLFlow instance
- Room for configurability left in design

**Storage**:
- SQLite as default local storage
- Hooks for other storage backends left open

**Future Integrations** (options left open):
- Telegram for managing/triggering workflows
- WhatsApp for managing/triggering workflows
- Human-in-the-loop capabilities

---

### What Went Wrong

**Agent's Claims**:
- Requirements being met
- Tests passing (98% claimed)

**Reality** (discovered via manual testing):
- Documentation gaps
- Broken functionalities
- Required extensive patching
- System "somewhat usable" but overwhelming

**User's Response**:
- Marked system as broken
- Removed autonomous agent
- Decided to fix things manually (same approach as pre-v0.1)

---

### User's Cleanup Vision

**Approach**:
1. Read and understand all documentation
2. Manual testing step by step
3. Fix and restructure/realign with original vision
4. Document everything for reference
5. Track all commands for reproducibility

**Key Principle**: Systematically assess and fix, not wholesale rewrite

---

## Part 2: Git Reference Commands

### Accessing Key Commits

```bash
# Current branch
git branch
# Output: * dev

# Fetch the stable v0.1 commit (f0a4f96)
git fetch origin f0a4f9601fbf1993cf606726dae2483befadc6b5
# After fetch, accessible via FETCH_HEAD

# The broken state commit is in local history
# 90d6bb9 - "Broken state: Messed up documentation..."

# View commit history
git log --oneline -20
```

### Reading Files from Specific Commits

```bash
# List all .md files from stable v0.1
git ls-tree -r --name-only FETCH_HEAD | grep -E "\.(md|MD)$"

# List all .md files from broken state
git ls-tree -r --name-only 90d6bb9 | grep -E "\.(md|MD)$"

# Read specific file from stable v0.1
git show FETCH_HEAD:<filepath>
# Example: git show FETCH_HEAD:docs/PROJECT_VISION.md

# Read specific file from broken state
git show 90d6bb9:<filepath>
# Example: git show 90d6bb9:.planning/STATE.md

# Get PR #1 details (the merge that created v0.1)
gh pr view 1 --json mergeCommit,headRefOid,baseRefOid
# Output: headRefOid = f0a4f9601fbf1993cf606726dae2483befadc6b5
```

### Commit References

| Reference | Hash | Description |
|-----------|------|-------------|
| Stable v0.1 | `f0a4f9601fbf1993cf606726dae2483befadc6b5` | "Release v0.1" - Last known good state |
| Broken state | `90d6bb9` | Agent's final state with all expansion |
| PR #1 merge | `9f51b9a84a7498617194c212503c55ad26df0593` | Merge commit |
| Current HEAD | `1f7e0e7` | "CL-002: Documentation index and cleanup" |

### Branches to Ignore

```bash
# These are NOT relevant to original project vision:
remotes/origin/barebones
remotes/origin/chat_builder
remotes/origin/gsd
```

---

## Part 3: Key Files Reference

### From Stable v0.1 (f0a4f96) - Format/Structure

| File | Purpose | Key Content |
|------|---------|-------------|
| `CLAUDE.md` | AI workflow instructions | Change levels, approval rules |
| `README.md` | Project overview | Features, roadmap, quickstart |
| `CHANGELOG.md` | Version history | Keep a Changelog format |
| `docs/PROJECT_VISION.md` | Philosophy & goals | Local-first, fail-fast, phases |
| `docs/ARCHITECTURE.md` | System design | Patterns, components, data flow |
| `docs/SPEC.md` | Schema specification | Complete config schema v1.0 |
| `docs/TASKS.md` | Work breakdown | Task format, status tracking |
| `docs/CONTEXT.md` | Session context | Quick resume format |
| `docs/adr/*` | Decision records | 18 ADRs with rationale |

### From Broken State (90d6bb9) - Information Content

| File | Purpose | Key Content |
|------|---------|-------------|
| `.planning/PROJECT.md` | Expanded vision | Enterprise platform description |
| `.planning/REQUIREMENTS.md` | v1.0/v1.2 requirements | Feature checklist |
| `.planning/STATE.md` | Reality check | Bugs, blockers, admission of broken state |
| `.planning/ROADMAP.md` | 11 phases | Expanded roadmap |
| `.planning/codebase/ARCHITECTURE.md` | Code architecture | Layer descriptions |
| `.planning/codebase/STRUCTURE.md` | File layout | Directory purposes |
| `.planning/phases/*` | Phase execution | Plans and summaries |
| `.planning/milestones/*` | Milestone tracking | Requirements, audits |

---

## Part 4: Entity Clarification

### Workflows vs Agents (User Clarification)

**User's Statement**:
> "Our system does WORKFLOWS. A well-designed workflow could be called an Agent, so I guess that's why, but it's confusing. I don't know why the autonomous agent made Agents and Workflows as two separate entities."

**Intended Model**:
- The system executes **WORKFLOWS**
- A workflow IS the primary entity
- An "Agent" is just a well-designed workflow (conceptually same thing)
- Should NOT be treated as separate entity types

**Agent's Model** (from 90d6bb9):
- Created separate Agent Registry
- Created separate Workflow Registry
- Bidirectional discovery between them
- This added unnecessary complexity

**Resolution Needed**: Simplify back to single entity (Workflow) model

---

## Part 5: Architecture Summary

### Intended Architecture (from user explanation)

```
┌─────────────────────────────────────────────────────────────────┐
│                    INTERACTION LAYER                             │
│  ┌──────────┐  ┌──────────────┐  ┌─────────────────────────────┐│
│  │   CLI    │  │  Python API  │  │  Dashboard UI (OPTIONAL)    ││
│  └──────────┘  └──────────────┘  │  - Chat interface           ││
│                                   │  - Workflow registry        ││
│                                   │  - MLFlow UI (embedded)     ││
│                                   │  - Execution histories      ││
│                                   └─────────────────────────────┘│
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      CORE ENGINE                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Config Parse │→│   Validate   │→│  Execute (LangGraph)   │  │
│  │  (Pydantic)  │  │  (Fail-fast) │  │  - Multi-LLM          │  │
│  └──────────────┘  └──────────────┘  │  - Tools              │  │
│                                       │  - Memory             │  │
│                                       │  - Branching/Loops    │  │
│                                       └───────────────────────┘  │
└───────────────────────────┬─────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌─────────────────────────┐   ┌─────────────────────────────────┐
│    DIRECT EXECUTION     │   │      DEPLOYED CONTAINER         │
│  - Run once, get output │   │  - Standalone Docker            │
│  - In-memory            │   │  - Reusable via API             │
│                         │   │  - Tracing only (NOT full MLFlow)│
│                         │   │  - Sends data to MLFlow host    │
└─────────────────────────┘   └─────────────────────────────────┘
                                          │
                                          ▼
                              ┌─────────────────────────────┐
                              │   MLFLOW (Full Instance)    │
                              │  - Sidecar or hosted        │
                              │  - Receives traces          │
                              │  - UI, evaluations, etc.    │
                              └─────────────────────────────┘
```

### Container Size Issue

**Problem at v0.1**: Each deployed Docker container was ~1.6GB because it included full MLFlow UI

**Intended Solution**:
- Deployed containers: Only tracing/observability part (lightweight)
- Full MLFlow: Runs separately (sidecar or hosted)
- Containers send trace data to central MLFlow instance

---

## Part 6: Testing Approach

### User's Preferred Approach

1. **Manual testing first** - Step by step verification
2. **Fix as we go** - Don't batch fixes
3. **Document findings** - Track what works, what doesn't
4. **Realign with vision** - Not just fix bugs, ensure alignment

### Testing Priority (inferred from vision)

| Priority | Component | Why |
|----------|-----------|-----|
| P0 | CLI workflow execution | Core functionality |
| P0 | Docker deployment | Core persistence model |
| P1 | Python API | Programmatic access |
| P1 | MLFlow observability | Cost tracking, debugging |
| P2 | Dashboard UI | Optional but useful |
| P2 | Multi-LLM | Extended capability |
| P3 | Webhooks | Future feature |
| P3 | Code sandboxes | Future feature |

---

## Part 7: Current State Summary

### Files in Working Directory

**Tracked (recent commits)**:
```
1f7e0e7 CL-002: Documentation index and cleanup
9d384f2 CL-001: Mark task as complete
66fd643 CL-001: Documentation reorganization and cleanup
70d4d68 CL01: Removed GSD
90d6bb9 Broken state: ...
```

**Untracked (temporary)**:
- `docs/development/SESSION_REQUIREMENTS.md` - To be deleted
- `docs/development/CL-003_CONSOLIDATION.md` - Detailed comparison
- `docs/development/CL-003_MASTER_REFERENCE.md` - This file

### Known Broken Components (from STATE.md)

| Component | Issue | Agent's Fix Status |
|-----------|-------|-------------------|
| CLI run | UnboundLocalError | Fixed |
| CLI deploy | Required Docker for generate mode | Fixed |
| Dashboard Workflows | Missing macros.html | Fixed |
| Dashboard Agents | Jinja2 underscore import | Fixed |
| Dashboard MLFlow | Returns 404 | Fixed |
| Dashboard Optimization | MLFlow filesystem errors | Fixed |
| **Chat UI** | **Multi-turn conversations crash** | **NOT FIXED** |
| **Chat UI** | **Download/Validate crash** | **NOT FIXED** |

### Need to Verify

- [ ] Does CLI `run` actually work now?
- [ ] Does CLI `validate` work?
- [ ] Does CLI `deploy` work?
- [ ] Does Docker deployment produce working container?
- [ ] Does deployed container API work?
- [ ] Does MLFlow tracking work?
- [ ] What is actual container size now?
- [ ] Does Dashboard load?
- [ ] Does Chat UI work?
- [ ] What features from expansion are actually functional?

---

## Part 8: Cleanup Process

### Phase 1: Verification (Current)
1. ✅ Read all documentation from both commits
2. ✅ Document user's vision and intent
3. ✅ Create reference documents
4. ⏳ Manual testing of each component
5. ⏳ Document what works vs broken

### Phase 2: Planning (Next)
- Based on verification, create prioritized fix list
- Identify what to keep vs discard
- Create task breakdown

### Phase 3: Execution (Later)
- Fix issues systematically
- Test each fix manually
- Document everything
- Follow f0a4f96 documentation formats

---

## Appendix: Quick Command Reference

```bash
# Read file from stable v0.1
git show FETCH_HEAD:<path>

# Read file from broken state
git show 90d6bb9:<path>

# List files in commit
git ls-tree -r --name-only <commit>

# Check current status
git status

# View recent commits
git log --oneline -10

# Fetch stable v0.1 if needed
git fetch origin f0a4f9601fbf1993cf606726dae2483befadc6b5
```

---

*This document serves as the master reference for the CL-003 cleanup process.*
*Update as new information is discovered or decisions are made.*
