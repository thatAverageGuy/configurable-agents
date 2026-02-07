# Test Configurations

Systematic test suite for verifying codebase functionality.
Run these in order to identify which features work and which are broken.

## Test Matrix

| # | Config | Feature Tested | Prerequisites |
|---|--------|----------------|---------------|
| 01 | `01_basic_linear.yaml` | Minimal linear flow | GOOGLE_API_KEY |
| 02 | `02_with_observability.yaml` | MLFlow tracking | GOOGLE_API_KEY |
| 03 | `03_multi_node_linear.yaml` | Multi-node sequence | GOOGLE_API_KEY |
| 04 | `04_with_tools.yaml` | Tool binding/execution | GOOGLE_API_KEY, SERPER_API_KEY |
| 05 | `05_conditional_branching.yaml` | Conditional routing | GOOGLE_API_KEY |
| 06 | `06_loop_iteration.yaml` | Loop execution | GOOGLE_API_KEY |
| 07 | `07_parallel_execution.yaml` | Fork-join parallel | GOOGLE_API_KEY |
| 08 | `08_multi_llm.yaml` | Per-node LLM override | GOOGLE_API_KEY, OPENAI_API_KEY |
| 09 | `09_with_memory.yaml` | Persistent memory | GOOGLE_API_KEY |
| 10 | `10_with_sandbox.yaml` | Code sandbox | GOOGLE_API_KEY |
| 11 | `11_with_storage.yaml` | SQLite persistence | GOOGLE_API_KEY |
| 12 | `12_full_featured.yaml` | All features combined | All API keys |

## Quick Test Commands

```bash
# Phase 1: Core Functionality
configurable-agents validate test_configs/01_basic_linear.yaml
configurable-agents run test_configs/01_basic_linear.yaml --input message="Hello"

# Phase 2: Observability
configurable-agents run test_configs/02_with_observability.yaml --input message="Test MLFlow"

# Phase 3: Multi-Node
configurable-agents run test_configs/03_multi_node_linear.yaml --input topic="Python"

# Phase 4: Tools
configurable-agents run test_configs/04_with_tools.yaml --input query="Python programming"

# Phase 5: Conditionals
configurable-agents run test_configs/05_conditional_branching.yaml --input sentiment="positive"
configurable-agents run test_configs/05_conditional_branching.yaml --input sentiment="negative"

# Phase 6: Loops
configurable-agents run test_configs/06_loop_iteration.yaml --input count="3"

# Phase 7: Fork-Join Parallel
configurable-agents run test_configs/07_parallel_execution.yaml --input topic="AI"

# Phase 8: Multi-LLM
configurable-agents run test_configs/08_multi_llm.yaml --input question="What is 2+2?"

# Phase 9: Memory
configurable-agents run test_configs/09_with_memory.yaml --input message="Remember my name is Alice"
configurable-agents run test_configs/09_with_memory.yaml --input message="What is my name?"

# Phase 10: Sandbox
configurable-agents run test_configs/10_with_sandbox.yaml --input task="Calculate fibonacci of 10"

# Phase 11: Storage
configurable-agents run test_configs/11_with_storage.yaml --input message="Test storage"

# Phase 12: Full Integration
configurable-agents run test_configs/12_full_featured.yaml --input query="Latest AI news" --input depth="shallow"
configurable-agents run test_configs/12_full_featured.yaml --input query="Latest AI news" --input depth="deep"
```

## Test Results Tracking

| # | Validate | Run | Notes |
|---|----------|-----|-------|
| 01 | ✅ | ✅ | Basic execution works |
| 02 | ✅ | ✅ | MLFlow works (cost summary fails) |
| 03 | ✅ | ✅ | Multi-node sequence works |
| 04 | ✅ | ❌ | Tool execution broken - no agent loop exists |
| 05 | ✅ | ✅ | **FIXED** - Conditional routing works! |
| 06 | ✅ | ✅ | **FIXED** - Loop iteration works! |
| 07 | ⏳ | ⏳ | Rewritten for fork-join, needs testing |
| 08 | ✅ | ✅ | Multi-LLM works (deprecation warning) |
| 09 | ✅ | ⚠️ | Memory not persisting between runs |
| 10 | ✅ | ✅ | Sandbox works! fib(10)=55 |
| 11 | ✅ | ⚠️ | Storage fails silently |
| 12 | ⏳ | ⏳ | Rewritten with correct edge syntax, needs testing |

Legend: ✅ Pass | ❌ Fail | ⚠️ Partial | ⏳ Pending

**Fixes Applied (2026-02-08)**:
1. Annotated reducers in state_builder.py for LangGraph compatibility
2. Corrected YAML syntax: `routes:` for conditionals, `loop:` block for loops
3. Replaced MAP parallel (Send-based) with fork-join parallel (`to: [node_a, node_b]`)

**Global Issue**: Storage backend fails on ALL runs with "too many values to unpack"

See `docs/development/implementation_logs/phase_5_cleanup_and_verification/CL-003_TEST_FINDINGS.md` for detailed issue tracking.

## Feature Complexity Breakdown

### Basic (01-03)
- Linear flow execution
- State passing between nodes
- Structured output validation
- MLFlow tracing

### Intermediate (04-07)
- Tool binding and execution
- Conditional edge routing
- Loop iteration with max bounds
- Fork-join parallel execution

### Advanced (08-11)
- Multi-LLM provider support
- Persistent memory across runs
- Code execution sandbox
- SQLite storage persistence

### Integration (12)
- All features working together
- Complex routing with conditionals + loops
- Full observability and persistence
