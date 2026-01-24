# Development Setup

## Quick Setup (Recommended)

**Automated setup script** - Creates venv, installs dependencies:

```bash
# Windows
setup.bat

# macOS/Linux
./setup.sh
```

The script will:
- ✅ Check if `.venv` exists (skips creation if already present)
- ✅ Create virtual environment if needed
- ✅ Activate the environment
- ✅ Install all dependencies (core + dev)

Then activate the virtual environment:
```bash
# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate
```

---

## Manual Installation

If you prefer to set up manually or the script doesn't work:

### 1. Clone the repository
```bash
git clone <repository-url>
cd configurable-agents
```

### 2. Create and activate virtual environment
```bash
python -m venv .venv

# On Windows
.venv\Scripts\activate

# On macOS/Linux
source .venv/bin/activate
```

### 3. Install dependencies
```bash
# Install core dependencies
pip install -e .

# Install development dependencies (includes pytest, etc.)
pip install -e ".[dev]"
```

### 4. Set up environment variables
```bash
# Copy example env file
cp .env.example .env

# Edit .env and add your API keys
# - GOOGLE_API_KEY (get from: https://makersuite.google.com/app/apikey)
# - SERPER_API_KEY (get from: https://serper.dev)
```

### 5. Verify installation
```bash
# Test package import
python -c "import configurable_agents; print(configurable_agents.__version__)"

# Run tests
pytest tests/test_setup.py -v
```

## Project Structure

```
configurable-agents/
├── src/
│   └── configurable_agents/
│       ├── __init__.py
│       ├── logging_config.py
│       ├── config/          # Config parsing and validation (T-002, T-003, T-004)
│       ├── core/            # Core execution components (T-006, T-007, T-011, T-012)
│       ├── llm/             # LLM provider integration (T-009)
│       ├── tools/           # Tool registry (T-008)
│       └── runtime/         # Runtime executor (T-013)
├── tests/
│   ├── config/
│   ├── core/
│   ├── llm/
│   ├── tools/
│   ├── runtime/
│   └── integration/
├── docs/                    # Architecture Decision Records and specs
├── pyproject.toml          # Project dependencies and configuration
├── pytest.ini              # Pytest configuration
├── .env.example            # Environment variable template
└── README.md

```

## Development Workflow

### Running tests
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/config/test_parser.py

# Run with coverage
pytest --cov=configurable_agents --cov-report=html

# Skip slow tests
pytest -m "not slow"

# Skip integration tests (require API keys)
pytest -m "not integration"
```

### Code formatting
```bash
# Format code
black src/ tests/

# Lint code
ruff check src/ tests/

# Type checking
mypy src/
```

## Next Steps

See `docs/TASKS.md` for the implementation roadmap.

Current status: **T-001 (Project Setup) - COMPLETE ✅**

Next task: **T-002 (Config Parser)**
