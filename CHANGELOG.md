# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### In Progress
- T-002: Config Parser (next)

---

## [0.1.0-dev] - 2026-01-24

### Added - T-001: Project Setup ✅

**Commit**: T-001: Project setup - Package structure and dependencies

**What Was Done**:
- Created Python package structure (`src/configurable_agents/`)
- Set up all core modules: `config/`, `core/`, `llm/`, `tools/`, `runtime/`
- Configured dependencies in `pyproject.toml`
- Created development environment setup files
- Added logging configuration
- Set up comprehensive test structure
- Created development documentation

**Files Created**:
```
src/configurable_agents/
├── __init__.py (v0.1.0-dev)
├── logging_config.py
├── config/__init__.py
├── core/__init__.py
├── llm/__init__.py
├── tools/__init__.py
└── runtime/__init__.py

tests/
├── __init__.py
├── conftest.py (shared fixtures)
├── test_setup.py (verification tests)
└── {config,core,llm,tools,runtime,integration}/

Configuration:
├── pyproject.toml (dependencies & project metadata)
├── pytest.ini (test configuration)
├── .env.example (API key template)
└── .gitignore (comprehensive Python patterns)

Documentation:
├── README.md (complete user-facing documentation)
├── SETUP.md (development setup guide)
└── CHANGELOG.md (this file)
```

**How to Verify**:

1. **Check package structure exists**:
   ```bash
   ls -la src/configurable_agents/
   # Should see: __init__.py, logging_config.py, and 5 subdirectories
   ```

2. **Verify package imports work**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); import configurable_agents; print(f'Version: {configurable_agents.__version__}')"
   # Expected output: Version: 0.1.0-dev
   ```

3. **Verify all submodules import**:
   ```bash
   python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents import config, core, llm, tools, runtime; print('All modules imported successfully')"
   # Expected output: All modules imported successfully
   ```

4. **Check dependencies are defined**:
   ```bash
   grep -A 10 "dependencies = \[" pyproject.toml
   # Should show: pydantic, pyyaml, langgraph, langchain, etc.
   ```

5. **Verify test structure**:
   ```bash
   ls -la tests/
   # Should see: __init__.py, conftest.py, test_setup.py, and subdirectories
   ```

6. **Check environment template exists**:
   ```bash
   cat .env.example
   # Should show: GOOGLE_API_KEY, SERPER_API_KEY placeholders
   ```

**What to Expect**:
- ✅ Clean package structure following Python best practices
- ✅ All imports work (no module errors)
- ✅ Test framework ready (pytest configured)
- ✅ Dependencies declared (not yet installed by user)
- ✅ Development documentation available
- ❌ No actual functionality yet (just structure)
- ❌ Tests will pass but modules are empty placeholders

**Next Steps for User**:
```bash
# Install the package in development mode
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env

# Edit .env with your API keys (not needed until T-009)
# GOOGLE_API_KEY=your-key-here

# Verify installation
python -c "import configurable_agents; print(configurable_agents.__version__)"

# Run setup verification tests
pytest tests/test_setup.py -v
```

**Dependencies Status**:
- Core: pydantic, pyyaml, langgraph, langchain, langchain-google-genai, python-dotenv
- Dev: pytest, pytest-cov, pytest-asyncio, black, ruff, mypy
- Status: Declared in pyproject.toml, not yet used in code

**Documentation Updated**:
- ✅ docs/TASKS.md (T-001 marked DONE, progress tracker added)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (complete rewrite with roadmap)
- ✅ SETUP.md (development guide created)
- ✅ CHANGELOG.md (this file created)

**Git Commit Command**:
```bash
git add .
git commit -m "T-001: Project setup - Package structure and dependencies

- Created src/configurable_agents/ package structure
- Set up config, core, llm, tools, runtime modules
- Configured pyproject.toml with all dependencies
- Added pytest configuration and test structure
- Created .env.example for API keys
- Updated .gitignore with comprehensive Python patterns
- Added logging_config.py for application logging
- Created SETUP.md development guide
- Rewrote README.md with roadmap and progress tracker
- Updated docs/TASKS.md and docs/DISCUSSION.md

Verification: python -c 'import sys; sys.path.insert(0, \"src\"); import configurable_agents; print(configurable_agents.__version__)'
Expected: 0.1.0-dev

Progress: 1/20 tasks (5%) - Foundation phase
Next: T-002 (Config Parser)"
```

---

## Template for Future Tasks

```markdown
## [Version] - YYYY-MM-DD

### Added - T-XXX: Task Name ✅

**Commit**: T-XXX: Brief description

**What Was Done**:
- Bullet points of changes

**Files Created/Modified**:
- List of files

**How to Verify**:
1. Command to run
2. Expected output

**What to Expect**:
- ✅ What works
- ❌ What doesn't work yet

**Next Steps for User**:
- Commands to run
- What to test

**Git Commit Command**:
```bash
git add .
git commit -m "..."
```
```

---

## Notes

- Each task gets one commit
- CHANGELOG updated before commit
- Verification steps included for reproducibility
- Progress tracked in both CHANGELOG and docs/TASKS.md
- Version stays at 0.1.0-dev until v0.1 release
