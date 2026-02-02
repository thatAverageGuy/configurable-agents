# Coding Conventions

**Analysis Date:** 2026-02-02

## Naming Patterns

**Files:**
- Lowercase with underscores: `node_executor.py`, `state_builder.py`, `config_parser.py`
- Test files: `test_<module>.py` (e.g., `test_node_executor.py`)
- Module files follow single-responsibility: `parser.py`, `schema.py`, `validator.py`, `types.py`

**Functions:**
- Lowercase with underscores: `execute_node()`, `resolve_prompt()`, `extract_variables()`
- Private functions prefixed with single underscore: `_strip_state_prefix()`, `_find_similar()`, `_parse_file()`
- Factory functions use `create_` prefix: `create_llm()`, `build_output_model()`, `build_state_model()`

**Variables:**
- Lowercase with underscores for local variables: `merged_llm_config`, `resolved_inputs`, `node_id`
- Constants in UPPERCASE: `"DEBUG"`, `"INFO"`, `"ERROR"` (logging levels)
- Loop counters and temporaries use descriptive names: `for i, call in enumerate(self.calls, 1)`

**Types & Classes:**
- PascalCase for classes: `NodeConfig`, `WorkflowConfig`, `FlowMetadata`, `OutputSchema`
- Custom exceptions inherit from Exception: `NodeExecutionError`, `ConfigParseError`, `ValidationError`, `LLMConfigError`
- Exception names end with `Error`: All custom exceptions follow this pattern
- Pydantic models use PascalCase: `BaseModel` subclasses are `NodeConfig`, `StateFieldConfig`, etc.

## Code Style

**Formatting:**
- Line length: 100 characters (configured in `pyproject.toml`)
- Tool: `black` (v23.0.0+) for auto-formatting
- Target Python versions: 3.10, 3.11, 3.12

**Linting:**
- Tool: `ruff` (v0.1.0+)
- Enabled rules:
  - E: pycodestyle errors
  - W: pycodestyle warnings
  - F: pyflakes
  - I: isort (import sorting)
  - B: flake8-bugbear
  - C4: flake8-comprehensions
- Configuration in `pyproject.toml` under `[tool.ruff]`

**Type Checking:**
- Tool: `mypy` (v1.5.0+)
- Setting: `disallow_untyped_defs = true` (all functions must have type annotations)
- Python version: 3.10+
- Warnings enabled for `return_any` and `unused_configs`

## Import Organization

**Order:**
1. Standard library imports (stdlib): `import logging`, `import json`, `from pathlib import Path`
2. Third-party imports: `from pydantic import BaseModel`, `from langchain_core...`
3. Local application imports: `from configurable_agents.config import...`

**Path Aliases:**
- No aliases used; full paths are explicit: `from configurable_agents.config.schema import NodeConfig`
- Uses package structure directly: `configurable_agents.config`, `configurable_agents.core`, `configurable_agents.llm`

**TYPE_CHECKING imports:**
- Used for circular dependency avoidance: `from typing import TYPE_CHECKING` at top, then `if TYPE_CHECKING: from configurable_agents.observability import MLFlowTracker`
- Example in `src/configurable_agents/core/node_executor.py` lines 38-39

## Error Handling

**Patterns:**
- Custom exception classes with contextual information (see `src/configurable_agents/config/schema.py`, `src/configurable_agents/llm/provider.py`)
- Exceptions include metadata fields: `reason`, `provider`, `suggestion`, `node_id`
- Try-catch blocks wrap distinct operations and provide context in re-raised exceptions
- Pattern: Catch specific exceptions, add context, re-raise as domain-specific exception (example: `src/configurable_agents/core/node_executor.py` lines 144-319)
- Error messages include:
  - What failed: `"Node execution failed"`
  - Context: `node_id`, operation step name
  - Suggestions: Helpful next steps when available (e.g., `LLMProviderError` suggests waiting for v0.2+)

**Fail-fast strategy:**
- Stop at first validation failure with helpful message (see `src/configurable_agents/config/validator.py`)
- Early returns with exceptions rather than continuing with invalid state

## Logging

**Framework:** Standard library `logging` module

**Patterns:**
- Module logger created via `logging.getLogger(__name__)` (see `src/configurable_agents/config/parser.py` line 11)
- Or via helper: `from configurable_agents.logging_config import get_logger` then `logger = get_logger(__name__)`
- Logger instance named `logger` (lowercase)
- Configured in `src/configurable_agents/logging_config.py` with setup function

**Usage levels:**
- `logger.debug()`: Detailed operation info (input/output counts, resolved values)
- `logger.info()`: Operation completion, success milestones
- `logger.warning()`: Non-fatal issues, deprecated patterns
- `logger.error()`: Errors (caught and handled)

**Style:**
- Include context in messages: `f"Node '{node_id}': {description}"`
- Log at operation boundaries (start/end) and error points
- Example (from `src/configurable_agents/core/node_executor.py`):
  - Line 166: `logger.debug(f"Node '{node_id}': Resolved {len(resolved_inputs)} input mappings...")`
  - Line 261: `logger.info(f"Node '{node_id}': LLM call successful")`

## Comments

**When to Comment:**
- Complex algorithms: regex patterns, edit distance calculation (see `src/configurable_agents/config/validator.py` lines 43-80)
- Design decisions and workarounds: See `src/configurable_agents/core/node_executor.py` lines 64-96 (state prefix stripping workaround)
- TODO/FIXME with task tracking: `# TODO T-011.1: Update template resolver...` (references task system)
- Inline comments before non-obvious code blocks

**What NOT to Comment:**
- Self-documenting code: clear variable names eliminate need for comments
- One-liners where intent is obvious
- Code that mirrors docstring

**Style:**
- Capitalize first letter: `# Update state with output values`
- Complete sentences for block comments
- Inline comments preceded by two spaces: `value = x  # Resolved input value`

## Docstrings

**Format:** Google-style docstrings (not strict but follows the pattern)

**Elements:**
- Summary (one-line description)
- Blank line
- Detailed description (if needed)
- Args: (parameter names, types, descriptions)
- Returns: (type and description)
- Raises: (exception types and when)
- Examples: (usage examples with >>> prefix)

**Examples from codebase:**
- `src/configurable_agents/core/node_executor.py` lines 105-141: Full function docstring
- `src/configurable_agents/config/parser.py` lines 24-40: Method docstring with Args/Returns/Raises

**Module docstrings:**
- Three-line format:
  - One-line summary
  - Blank line
  - Detailed purpose and context
- Example: `src/configurable_agents/core/node_executor.py` lines 1-17

## Function Design

**Size:** Functions are focused and typically 20-60 lines

**Parameters:**
- Explicit type annotations required (mypy `disallow_untyped_defs`)
- Use descriptive names: `node_config`, `resolved_inputs`, not `cfg`, `inputs`
- Optional parameters use `Optional[Type]` with `None` defaults
- Pattern: `def func(required: str, optional: Optional[str] = None) -> ReturnType`

**Return Values:**
- Explicit return types required
- Return new instances for state updates (immutable pattern): `new_state = state.model_copy()`
- Return tuples for multiple values: `(result, usage)` from LLM calls
- Return custom types (Pydantic models) for structured data

**Copy-on-write pattern:**
- Used for state updates: `new_state = state.model_copy()` then modify via `setattr()`
- Example: `src/configurable_agents/core/node_executor.py` lines 278-299

## Module Design

**Exports:**
- Public API defined via imports in `__init__.py` files
- Example: `src/configurable_agents/core/__init__.py` exports `execute_node`, `build_graph`, etc.
- Private functions/classes left in implementation files (not re-exported)

**Barrel Files:**
- Used for subpackage APIs: `src/configurable_agents/core/__init__.py` imports and re-exports main functions
- Reduces import depth: allows `from configurable_agents.core import execute_node` instead of `from configurable_agents.core.node_executor import execute_node`

**Class Design:**
- Pydantic models for configuration and data: `src/configurable_agents/config/schema.py`
- Service classes (e.g., `ConfigLoader`) with public methods
- Helper/utility functions at module level (not class methods)
- Exception classes are lightweight: store context fields, provide formatted messages in `__init__`

## Validation

**Pydantic validators:**
- Use `@field_validator` for single-field validation
- Use `@model_validator(mode="after")` for cross-field validation
- Return validated value or raise `ValueError` with message
- Examples: `src/configurable_agents/config/schema.py` lines 27-33 (FlowMetadata), lines 55-60 (StateFieldConfig)

**Custom validation:**
- Dedicated validation module: `src/configurable_agents/config/validator.py`
- Separate from schema: schema defines structure, validator enforces cross-reference rules
- Validation errors include suggestions for fixes

---

*Convention analysis: 2026-02-02*
