# T-002: Config Parser

**Status**: ✅ Complete
**Completed**: 2026-01-24
**Commit**: `ba6c15e` - T-002: Config parser - YAML and JSON support
**Phase**: Phase 1 (Foundation)
**Progress After**: 2/20 tasks (10%)

---

## 🎯 What Was Done

- Implemented `ConfigLoader` class for loading YAML/JSON files
- Auto-detects format from file extension (.yaml, .yml, .json)
- Handles both absolute and relative file paths
- Comprehensive error handling with helpful messages
- Convenience function `parse_config_file()` for simple use cases
- Created 18 comprehensive unit tests for parser (all pass)
- Created 3 setup verification tests
- **Total tests**: 21 tests passing
- Test fixtures for valid/invalid YAML and JSON
- **Automated setup scripts** for one-command venv setup (Windows & Unix)
- Setup scripts check if venv exists to avoid redundant installations

---

## 📦 Files Created

### Source Code

```
src/configurable_agents/config/
├── parser.py (ConfigLoader class + parse_config_file function)
└── __init__.py (exports public API)
```

### Tests

```
tests/config/
├── __init__.py
├── test_parser.py (18 test functions)
└── fixtures/
    ├── valid_config.yaml
    ├── valid_config.json
    ├── invalid_syntax.yaml
    └── invalid_syntax.json
```

### Development Setup

```
├── setup.bat (Windows automated setup)
├── setup.sh (Unix/Linux/macOS automated setup)
└── SETUP.md (updated with Quick Setup section)
```

---

## 🔧 How to Verify

### 1. Test imports work

```bash
python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file, ConfigLoader; print('Imports OK')"
# Expected: Imports OK
```

### 2. Load a YAML file

```bash
python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.yaml'); print('Flow:', config['flow']['name'])"
# Expected: Flow: test_workflow
```

### 3. Load a JSON file

```bash
python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; config = parse_config_file('tests/config/fixtures/valid_config.json'); print('Flow:', config['flow']['name'])"
# Expected: Flow: test_workflow
```

### 4. Test error handling (file not found)

```bash
python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('missing.yaml')"
# Expected: FileNotFoundError: Config file not found: missing.yaml
```

### 5. Test error handling (invalid syntax)

```bash
python -c "import sys; sys.path.insert(0, 'src'); from configurable_agents.config import parse_config_file; parse_config_file('tests/config/fixtures/invalid_syntax.yaml')"
# Expected: ConfigParseError: Invalid YAML syntax...
```

### 6. Run automated setup (recommended)

```bash
# Windows
setup.bat

# Unix/Linux/macOS
./setup.sh
# Expected: Virtual environment created, dependencies installed
```

### 7. Run full test suite

```bash
.venv/Scripts/pytest tests/config/test_parser.py -v  # Windows
.venv/bin/pytest tests/config/test_parser.py -v      # Unix
# Expected: 18 passed in ~0.1s
```

---

## ✅ What to Expect

**Working**:
- ✅ Load YAML files (.yaml, .yml extensions)
- ✅ Load JSON files (.json extension)
- ✅ Auto-detect format from extension
- ✅ Both absolute and relative paths work
- ✅ Clear error messages for file not found
- ✅ Clear error messages for syntax errors
- ✅ Raises `ConfigParseError` for unsupported extensions

**Not Yet Working**:
- ❌ No validation yet (returns raw dict, validation is T-004)
- ❌ No programmatic dict loading yet (just files)

---

## 💻 Public API

### Recommended Usage (Convenience Function)

```python
from configurable_agents.config import parse_config_file

config = parse_config_file("workflow.yaml")  # or .json
# Returns: dict with config structure
```

### Advanced Usage (Class)

```python
from configurable_agents.config import ConfigLoader

loader = ConfigLoader()
config = loader.load_file("workflow.yaml")
# Returns: dict with config structure
```

### Error Handling

```python
from configurable_agents.config import ConfigParseError

try:
    config = parse_config_file("config.yaml")
except FileNotFoundError:
    print("File not found")
except ConfigParseError as e:
    print(f"Parse error: {e}")
```

---

## 📚 Dependencies Used

- `pyyaml` - YAML parsing
- `json` (built-in) - JSON parsing
- `pathlib` (built-in) - Path handling

---

## 💡 Design Decisions

### Why auto-detect format from extension?

- Simpler API (no format parameter needed)
- Less error-prone (can't mismatch format and file)
- Standard practice for config loaders

### Why raise ConfigParseError?

- Distinguishes parse errors from other errors
- Allows callers to handle parse errors specifically
- Wraps underlying YAML/JSON errors with context

### Why support both YAML and JSON?

- YAML is human-friendly (main format)
- JSON is machine-friendly (API integration)
- Same config works in both formats

---

## 🧪 Tests Created

**File**: `tests/config/test_parser.py`

**Test Categories** (18 tests total):
1. **YAML loading** (4 tests)
   - Load valid YAML file
   - Load .yml extension
   - Handle YAML syntax errors
   - Handle invalid YAML structure

2. **JSON loading** (4 tests)
   - Load valid JSON file
   - Handle JSON syntax errors
   - Handle invalid JSON structure
   - Verify JSON round-trip

3. **Path handling** (4 tests)
   - Absolute paths
   - Relative paths
   - Non-existent files
   - Invalid file paths

4. **Error handling** (4 tests)
   - Unsupported extensions (.txt, .xml)
   - Empty files
   - Malformed content
   - Permission errors

5. **API convenience** (2 tests)
   - parse_config_file() function
   - ConfigLoader class

---

## 📖 Documentation Updated

- ✅ `docs/TASKS.md` - T-002 implementation details added
- ✅ `docs/ARCHITECTURE.md` - Component 1 updated
- ✅ `docs/DISCUSSION.md` - T-002 decisions documented

---

## 📝 Git Commit Template

```bash
git add .
git commit -m "T-002: Config parser - YAML and JSON support

- Implemented ConfigLoader class with YAML/JSON auto-detection
- Added parse_config_file() convenience function
- Support for .yaml, .yml, and .json file extensions
- Comprehensive error handling (FileNotFoundError, ConfigParseError)
- Both absolute and relative path support
- Created 18 unit tests with valid/invalid fixtures
- Exported public API from config module
- Added automated setup scripts (setup.bat, setup.sh)
- Setup scripts check for existing venv to avoid redundant installs
- Updated SETUP.md with Quick Setup section

Verification:
  ./setup.sh  # or setup.bat on Windows
  .venv/Scripts/pytest tests/config/test_parser.py -v
  Expected: 18 passed

Progress: 2/20 tasks (10%) - Foundation phase
Next: T-003 (Config Schema - Pydantic Models)"
```

---

## 🔗 Related Documentation

- **[../../TASKS.md](../../TASKS.md)** - Task T-002 acceptance criteria
- **[../../SPEC.md](../../SPEC.md)** - Config file format specification
- **[../../ARCHITECTURE.md](../../ARCHITECTURE.md)** - Config parsing component

---

*Implementation completed: 2026-01-24*
*Next task: T-003 (Config Schema - Pydantic Models)*
