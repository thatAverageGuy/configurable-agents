# T-014: CLI Interface

**Status**: ✅ Complete
**Completed**: 2026-01-27
**Commit**: T-014: CLI interface - Command-line tool for workflows
**Phase**: Phase 3 (Polish & UX)
**Progress After**: 15/20 tasks (75%)

---

## 🎯 What Was Done

- Implemented command-line interface for running and validating workflows
- `run` command: Execute workflows from YAML/JSON files
- `validate` command: Validate configs without executing
- Smart input parsing with automatic type detection (str, int, bool, list, dict)
- Pretty color-coded terminal output with Unicode fallback for Windows
- Comprehensive error handling with helpful messages
- Verbose mode for debugging with full tracebacks
- 37 comprehensive unit tests + 2 integration tests
- Total: 443 tests passing (up from 406)

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/
├── cli.py (367 lines - CLI logic with argparse)
└── __main__.py (14 lines - module entry point)
```

### Tests

```
tests/
└── test_cli.py (597 lines, 37 unit tests + 2 integration tests)
```

### Documentation

```
examples/
└── README.md (updated with CLI usage examples)
```

---

## 🔧 How to Verify

### 1. Test CLI

```bash
pytest tests/test_cli.py -v -m "not integration"
# Expected: 37 passed
```

### 2. Run integration tests

```bash
pytest tests/test_cli.py -v -m integration
# Expected: 2 integration tests
```

### 3. Run full test suite

```bash
pytest -v -m "not integration"
# Expected: 443 passed (37 cli + 406 existing)
```

### 4. Use CLI

```bash
# Validate a config
configurable-agents validate examples/simple_workflow.yaml

# Run a workflow
configurable-agents run examples/simple_workflow.yaml --input name="Alice"

# Verbose mode
configurable-agents run workflow.yaml --input topic="AI" --verbose
```

---

## ✅ What to Expect

**Working**:
- ✅ Run workflows from command line
- ✅ Validate configs without execution
- ✅ Multiple inputs with type detection
- ✅ Verbose logging for debugging
- ✅ Pretty color-coded output
- ✅ Exit codes (0=success, 1=error)
- ✅ Two entry points: script and module
- ✅ Smart type parsing (str, int, bool, JSON)
- ✅ Helpful error messages

**Not Yet Working**:
- ❌ No interactive mode (v0.2+ feature)
- ❌ No workflow listing/discovery
- ❌ No output formatting options

---

## 💻 Public API

### CLI Commands

```bash
# Main command with subcommands
configurable-agents <command> [options]

# Run command
configurable-agents run <config_path> --input <key=value> [--verbose]

# Validate command
configurable-agents validate <config_path> [--verbose]

# Help
configurable-agents --help
configurable-agents run --help
configurable-agents validate --help
```

### CLI Usage

```bash
# Run a workflow
configurable-agents run workflow.yaml --input topic="AI Safety"

# Validate a config
configurable-agents validate workflow.yaml

# Run with verbose logging
configurable-agents run workflow.yaml --input name="Alice" --verbose

# Multiple inputs with different types
configurable-agents run workflow.yaml \
  --input topic="AI" \
  --input count=5 \
  --input enabled=true \
  --input 'tags=["ai", "safety"]'

# Module invocation
python -m configurable_agents run workflow.yaml --input name="Bob"
```

### Input Parsing

```bash
# Strings (auto-detected)
--input name="Alice"     # "Alice"
--input name=Alice       # "Alice"

# Numbers (auto-detected)
--input count=5          # 5 (int)
--input score=3.14       # 3.14 (float)

# Booleans (auto-detected)
--input enabled=true     # True
--input active=false     # False

# Lists (JSON format)
--input 'tags=["ai", "safety"]'  # ["ai", "safety"]

# Objects (JSON format)
--input 'metadata={"author": "Alice", "version": 1}'
```

---

## 📚 Dependencies Used

### Standard Library Only

- `argparse` - CLI argument parsing
- `sys` - Exit codes, stdout/stderr
- `json` - JSON parsing for inputs
- `os` - TTY detection for colors

**Status**: No new dependencies required

---

## 💡 Design Decisions

### Why argparse?

- Standard library (no dependencies)
- Familiar to Python developers
- Automatic help generation
- Subcommand support
- Type-safe argument parsing

### Why Color Output?

- ANSI codes with TTY detection
- Color-coded success/error/info/warning
- Improves readability and UX
- Disable on non-TTY (pipe-friendly)

### Why Unicode Fallback?

- ASCII symbols for Windows console (✓ → +, ✗ → x)
- Better compatibility across platforms
- Graceful degradation
- Still readable without Unicode

### Why Smart Parsing?

- JSON.loads for type detection
- String fallback for non-JSON
- Automatic int/float/bool detection
- No type annotations needed from user

### Why Exit Codes?

- Standard Unix conventions
- 0 = success
- 1 = error
- Shell script integration
- CI/CD compatibility

### Why Two Entry Points?

- Script: `configurable-agents` (installed via pip)
- Module: `python -m configurable_agents` (development)
- Flexibility for different workflows
- Standard Python package pattern

---

## 🧪 Tests Created

**File**: `tests/test_cli.py` (37 unit + 2 integration tests)

### Test Categories (39 tests total)

#### Command Parsing (8 tests)

1. **Run Command** (4 tests)
   - Parse run command
   - Config path argument
   - Input arguments
   - Verbose flag

2. **Validate Command** (4 tests)
   - Parse validate command
   - Config path argument
   - Verbose flag
   - Help text

#### Input Parsing (12 tests)

1. **String Inputs** (3 tests)
   - Quoted strings
   - Unquoted strings
   - Empty strings

2. **Numeric Inputs** (3 tests)
   - Integers
   - Floats
   - Scientific notation

3. **Boolean Inputs** (2 tests)
   - true/false (lowercase)
   - True/False (capitalized)

4. **JSON Inputs** (4 tests)
   - JSON arrays
   - JSON objects
   - Nested JSON
   - Invalid JSON fallback to string

#### Output Formatting (8 tests)

1. **Color Output** (4 tests)
   - Success messages (green)
   - Error messages (red)
   - Info messages (blue)
   - Warning messages (yellow)

2. **TTY Detection** (4 tests)
   - Colors on TTY
   - No colors on non-TTY
   - Unicode symbols
   - ASCII fallback

#### Error Handling (6 tests)

1. **Error Messages** (6 tests)
   - ConfigLoadError formatting
   - ConfigValidationError formatting
   - StateInitializationError formatting
   - WorkflowExecutionError formatting
   - Verbose mode shows traceback
   - Non-verbose mode hides traceback

#### Exit Codes (3 tests)

1. **Success Exit** (1 test)
   - Exit code 0 on success

2. **Error Exit** (2 tests)
   - Exit code 1 on error
   - Error type doesn't affect code

#### Integration Tests (2 tests - marked)

1. **End-to-End** (2 tests)
   - Run workflow via CLI
   - Validate workflow via CLI

---

## 🎨 CLI Features

### Run Command

```bash
# Basic usage
configurable-agents run workflow.yaml --input topic="AI"

# Multiple inputs
configurable-agents run workflow.yaml \
  --input topic="AI Safety" \
  --input count=5 \
  --input enabled=true

# Verbose mode
configurable-agents run workflow.yaml --input name="Alice" --verbose

# Output
✓ Workflow executed successfully!

Result:
{
  "topic": "AI Safety",
  "article": "..."
}
```

### Validate Command

```bash
# Validate config
configurable-agents validate workflow.yaml

# Verbose mode
configurable-agents validate workflow.yaml --verbose

# Output
✓ Config is valid!

# Error output
✗ Validation failed: Node 'process': output 'result' not found in state
```

### Smart Input Parsing

```bash
# Auto-detect types
--input name="Alice"           # String
--input count=42               # Integer
--input score=3.14             # Float
--input enabled=true           # Boolean
--input 'tags=["a", "b"]'      # List
--input 'meta={"x": 1}'        # Dict

# Fallback to string
--input weird=not-json-format  # String "not-json-format"
```

### Pretty Output

```bash
# Success (green ✓)
✓ Config is valid!
✓ Workflow executed successfully!

# Error (red ✗)
✗ Failed to load config: File not found: workflow.yaml
✗ Validation failed: Missing required field: topic

# Info (blue ℹ)
ℹ Loading workflow: workflow.yaml
ℹ Executing node: research

# Warning (yellow ⚠)
⚠ Check that all required state fields are provided
⚠ Verbose mode enabled - showing detailed logs
```

### Error Messages

```bash
# ConfigLoadError
✗ Failed to load config: File not found: workflow.yaml

# ConfigValidationError
✗ Invalid config: Node 'process': output 'result' not found in state fields

# StateInitializationError
✗ Invalid inputs: Missing required field: topic

# WorkflowExecutionError
✗ Workflow execution failed: Node 'greet': GOOGLE_API_KEY not set

# With verbose flag
✗ Workflow execution failed: Node 'greet': GOOGLE_API_KEY not set
Traceback (most recent call last):
  ...
  [Full traceback shown]
```

---

## 🔧 Usage Examples

### 1. Simple Workflow

```bash
# Run echo workflow
configurable-agents run examples/echo.yaml --input message="Hello!"

# Output
✓ Workflow executed successfully!
Result: {"response": "Hello!"}
```

### 2. Article Writer

```bash
# Run article writer with web search
export SERPER_API_KEY="your-key"
configurable-agents run examples/article_writer.yaml \
  --input topic="AI Safety"

# Output
✓ Workflow executed successfully!
Result: {"article": "...", "word_count": 450}
```

### 3. Nested State

```bash
# Run with complex inputs
configurable-agents run examples/nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics", "philosophy"]'

# Output
✓ Workflow executed successfully!
Result: {"profile": {"name": "Alice", "interests": [...]}}
```

### 4. Validation

```bash
# Validate before running
configurable-agents validate examples/article_writer.yaml

# Output
✓ Config is valid!

# Invalid config
configurable-agents validate broken.yaml

# Output
✗ Validation failed: Node 'process': output 'result' not found in state
```

### 5. Verbose Mode

```bash
# Run with verbose logging
configurable-agents run workflow.yaml \
  --input topic="AI" \
  --verbose

# Output
ℹ Loading workflow: workflow.yaml
ℹ Validating config...
ℹ Building state model...
ℹ Initializing state with inputs: {'topic': 'AI'}
ℹ Building execution graph...
ℹ Executing workflow...
ℹ Executing node: research
ℹ Executing node: write
✓ Workflow executed successfully!
Result: {...}
```

---

## 📖 Integration Points

### Uses From Previous Tasks

- T-013: Runtime executor (`run_workflow`, `validate_workflow`)
- All 6 exception types from T-013
- Enables user-facing workflow execution

### Enables

- User-friendly workflow execution from command line
- CI/CD integration (exit codes)
- Shell script integration
- Quick workflow testing

---

## 📖 Documentation Updated

- ✅ CHANGELOG.md (comprehensive entry created)
- ✅ docs/TASKS.md (T-014 marked DONE, progress updated to 15/20)
- ✅ docs/DISCUSSION.md (status updated)
- ✅ README.md (progress statistics updated, CLI examples added)
- ✅ examples/README.md (CLI usage examples added)

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-014: CLI interface - Command-line tool for workflows

- Implemented command-line interface with argparse
  - run command: Execute workflows from YAML/JSON
  - validate command: Validate configs without execution
  - --input flag: Pass workflow inputs (multiple allowed)
  - --verbose flag: Enable debug logging
  - Two entry points: script and module

- Smart input parsing with type detection
  - Strings: --input name=\"Alice\" or --input name=Alice
  - Numbers: --input count=5 (auto-parsed to int)
  - Booleans: --input enabled=true (auto-parsed)
  - Lists: --input 'tags=[\"ai\", \"safety\"]' (JSON format)
  - Objects: --input 'metadata={\"author\": \"Alice\"}' (JSON)
  - Fallback to string for non-JSON values

- Pretty color-coded terminal output
  - Success messages (green ✓)
  - Error messages (red ✗)
  - Info messages (blue ℹ)
  - Warning messages (yellow ⚠)
  - ANSI codes with TTY detection
  - Unicode fallback for Windows (✓ → +, ✗ → x)

- Comprehensive error handling
  - All 6 exception types from T-013
  - Helpful error messages with suggestions
  - Verbose mode shows full tracebacks
  - Non-verbose mode shows clean errors
  - Exit code 0 for success, 1 for errors

- Created 39 comprehensive tests
  - 37 unit tests (parsing, formatting, errors)
  - 2 integration tests (end-to-end CLI execution)

- Entry points configured
  - Script: configurable-agents (via pip install)
  - Module: python -m configurable_agents (development)

Verification:
  pytest tests/test_cli.py -v -m 'not integration'
  Expected: 37 passed

  pytest -v -m 'not integration'
  Expected: 443 passed (37 cli + 406 existing)

Progress: 15/20 tasks (75%) - Phase 3 (Polish & UX) 1/5 complete
Next: T-015 (Example Configs)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-014 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - CLI specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - CLI architecture
- **[../../../examples/README.md](../../../examples/README.md)** - Usage examples

---

## 🚀 Next Steps for Users

### Install Package

```bash
# Install in development mode
pip install -e .

# Verify installation
configurable-agents --help

# Or use module entry point
python -m configurable_agents --help
```

### Run Your First Workflow

```bash
# Validate a config
configurable-agents validate examples/echo.yaml

# Run the workflow
configurable-agents run examples/echo.yaml --input message="Hello!"

# Run with verbose mode
configurable-agents run examples/echo.yaml \
  --input message="Debug me" \
  --verbose
```

### Shell Integration

```bash
#!/bin/bash
# run_workflow.sh

if configurable-agents validate workflow.yaml; then
    echo "Config valid, running workflow..."
    configurable-agents run workflow.yaml --input topic="$1"
else
    echo "Config invalid, aborting"
    exit 1
fi
```

---

## 📊 Phase 3 Progress

**Phase 3 (Polish & UX): 1/5 complete (20%)**
- ✅ T-014: CLI Interface
- ⏳ T-015: Example Configs
- ⏳ T-016: Documentation
- ⏳ T-017: Integration Tests
- ⏳ T-018: Error Message Improvements (future)

---

*Implementation completed: 2026-01-27*
*Next task: T-015 (Example Configs)*
