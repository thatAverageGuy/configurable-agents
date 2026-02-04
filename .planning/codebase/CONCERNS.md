# Codebase Concerns

**Analysis Date:** 2026-02-02

## Tech Debt

### Template Resolution {state.X} Syntax Workaround

**Issue**: Preprocessor stripping state prefix before template resolution

**Files**:
- `src/configurable_agents/core/node_executor.py:64-96` (_strip_state_prefix function)
- `src/configurable_agents/core/node_executor.py:16,75-76` (TODO T-011.1 references)

**Impact**:
- Code duplication: {state.field} syntax validated in config but stripped at runtime
- Maintenance burden: Template resolver doesn't handle native state prefix syntax
- Inconsistency: SPEC.md examples use {state.field}, but resolver expects {field}

**Current state**: Temporary workaround in place. The validator (ADR-004) accepts {state.field} syntax in prompts, but the template resolver (T-010) expects plain {field} syntax. Regex preprocessing (line 94-96) converts templates at runtime.

**Fix approach**:
1. Update `src/configurable_agents/core/template.py:resolve_prompt()` to recognize and handle {state.X} syntax natively
2. Update `resolve_variable()` to check state prefix and route accordingly
3. Remove _strip_state_prefix() preprocessing function
4. Update tests in `tests/core/test_template.py` to cover state. prefix syntax
5. Estimated effort: 2-4 hours

---

### State Persistence Gap (In-Memory Only)

**Issue**: No state persistence between workflow executions

**Constraint**: ADR-008 explicitly chooses in-memory state only for v0.1

**Files**:
- `src/configurable_agents/core/state_builder.py` (StateModel instantiation)
- `src/configurable_agents/runtime/executor.py:run_workflow()` (returns result, no save)
- ADR-008 documents this constraint

**Impact**:
- **Process crash**: Workflow loses all state mid-execution, must restart from beginning
- **Costs**: Repeats expensive LLM calls if process fails
- **Resumability**: No checkpoint/resume capability
- **Multi-worker**: Cannot share state across distributed execution
- **Production**: Limits reliability for long-running workflows

**Known limitation**: This is a deliberate v0.1 constraint (see ADR-008, line 50). Designed for short workflows (<30s) that complete reliably. Persistence deferred to v0.2+.

**Fix approach**:
1. Add optional state persistence layer (v0.2 feature)
2. Implement file-based checkpointing (simplest path)
3. Add optional Redis/PostgreSQL support (v0.2+)
4. Update executor to save state after each node execution
5. Add resume capability to CLI
6. Estimated effort: 2-3 days for basic file-based persistence

---

## Test Coverage Gaps

### Integration Test Coverage for Error Scenarios

**Issue**: Limited coverage of failure modes and edge cases

**Files**:
- `tests/integration/test_error_scenarios.py` exists but minimal coverage
- Limited tool failure testing
- No network timeout/error simulation

**Impact**:
- Tool API failures not thoroughly tested
- Edge cases may cause runtime crashes instead of graceful errors
- Error messages may be unclear in production

**Test status**: 645 passing tests exist (setup, config, core, deploy), but integration error scenarios undercovered.

**Fix approach**:
1. Expand `tests/integration/test_error_scenarios.py` with:
   - Tool API timeouts and failures
   - Invalid tool responses
   - LLM provider errors (rate limits, API keys)
   - Malformed state transitions
2. Mock external APIs consistently
3. Add chaos testing (simulated failures)
4. Estimated effort: 1-2 days

---

### Node Executor Error Context

**Issue**: Error handling in node_executor.py could be more specific

**Files**: `src/configurable_agents/core/node_executor.py:44-61` (NodeExecutionError class)

**Impact**:
- Generic error messages don't always pinpoint which node failed
- Stack traces can be confusing for users
- Debugging long workflows difficult

**Current state**: NodeExecutionError has node_id context, but not always populated in catch blocks.

**Fix approach**:
1. Ensure all try/except blocks set node_id when catching
2. Add phase context (input_mapping, prompt_resolution, llm_call, output_validation, state_update)
3. Include state snapshot in error context (sanitized)
4. Improve error messages with specific failure location
5. Estimated effort: 3-4 hours

---

## Fragile Areas

### CLI Module Size and Complexity

**Issue**: CLI module is monolithic

**Files**: `src/configurable_agents/cli.py` (958 lines)

**Why fragile**:
- Large file with multiple command handlers (run, validate, deploy, etc.)
- Mixing CLI argument parsing, business logic, and output formatting
- Difficult to test individual commands in isolation
- Adding new commands requires careful integration

**Impact**:
- Hard to test CLI features (would need subprocess calls or mocking)
- Changes to one command risk breaking others
- Error handling and validation scattered throughout

**Safe modification path**:
1. Consider breaking into submodules if adding more commands (v0.2)
2. Extract command handlers to separate functions with clear contracts
3. Use Click groups for command organization (already in place)
4. Add unit tests for individual handlers (mock run_workflow, parse_config_file, etc.)
5. Keep current approach for v0.1 (working and tested)

---

### Dynamic Model Creation (Pydantic)

**Issue**: Runtime model generation via create_model()

**Files**:
- `src/configurable_agents/core/state_builder.py:22-69` (build_state_model)
- `src/configurable_agents/core/output_builder.py` (similar pattern)

**Why fragile**:
- Pydantic models created at runtime from user config
- Type information lost in config parsing (strings like "str", "list[str]")
- Type coercion happens in get_python_type() - possible edge cases
- Custom nested object types require careful handling

**Impact**:
- Type mismatches at runtime instead of parse time
- Nested object schemas could accept invalid structures
- Performance: model creation on every workflow execution

**Known safe areas**:
- Basic types (str, int, float, bool) well-tested
- List/dict types covered
- Validation catches most errors

**Safe modification path**:
1. Add more comprehensive type validation tests (nested objects)
2. Cache created models if same workflow runs multiple times
3. Consider static type generation for frequently-used configs (future)
4. Keep runtime generation for flexibility

---

### LLM Provider Strategy Pattern

**Issue**: Strategy pattern for LLM providers incomplete

**Files**:
- `src/configurable_agents/llm/provider.py:20-50` (create_llm function)
- ADR-005 documents single-provider v0.1 constraint

**Why fragile**:
- Only Google Gemini implemented in v0.1
- Adding new providers requires modifying create_llm() function
- Provider validation happens at runtime, not parse time

**Impact**:
- Future multi-provider support may require refactoring
- Error messages for unknown providers could be clearer

**Known limitation**: This is deliberate v0.1 choice (see ADR-005). Single provider reduces complexity while allowing future expansion.

**Safe modification path**:
1. Validate provider in config validation phase (not runtime)
2. Prepare for v0.2 with provider-specific schema validation
3. Extract provider-specific defaults to separate files
4. Consider factory pattern enhancement for extensibility

---

## Security Considerations

### Environment Variable Handling

**Issue**: API keys passed via environment variables with minimal validation

**Files**:
- `src/configurable_agents/tools/serper.py` (SERPER_API_KEY)
- `src/configurable_agents/llm/google.py` (GOOGLE_API_KEY)
- ADR-013 documents environment variable strategy

**Current mitigation**:
- ✅ No hardcoded secrets
- ✅ Clear error messages for missing keys
- ✅ Isolated to tool/LLM initialization
- ✅ .env.example provided as template

**Risks**:
- ❌ Secrets might leak in logs if error messages too verbose (check in place)
- ❌ No secrets rotation mechanism
- ❌ No audit logging for API key access

**Recommendations**:
1. Ensure sensitive env vars never logged (current code compliant)
2. Add optional vault integration (v0.2+) via ADR or feature gate
3. Document secret management best practices in DEPLOYMENT.md
4. Consider ephemeral credentials for deployed containers

---

### Input Validation & Injection

**Issue**: User-provided prompts and state values passed to LLM without explicit validation

**Files**:
- `src/configurable_agents/core/template.py:resolve_prompt()` (variable resolution)
- `src/configurable_agents/core/node_executor.py:execute_node()` (prompt injection)

**Current mitigation**:
- ✅ Pydantic validates state field types
- ✅ Prompts are templates (not eval/exec)
- ✅ Tool outputs validated against schema

**Risks**:
- ❌ LLM prompt injection possible via state variables (inherent LLM risk, not system bug)
- ❌ No sandboxing of tool outputs before state update

**Recommendations**:
1. Document prompt injection awareness in security section
2. Sanitize tool outputs before LLM context (optional)
3. Add input validation rules (v0.2+ feature)
4. Consider using structured inputs for sensitive workflows

---

## Performance Bottlenecks

### Template Variable Resolution Loop

**Issue**: Linear search for each variable in prompt

**Files**: `src/configurable_agents/core/template.py:64-74` (resolve_prompt)

**Problem**:
```python
for var in variables:
    value = resolve_variable(var, inputs, state)
    resolved = resolved.replace(f"{{{var}}}", str(value))  # String replacement
```

**Impact**:
- O(V×P) complexity: V variables × P prompt length
- String replacement inefficient for large prompts
- Noticeable for workflows with 50+ variable references

**Cause**: Each variable requires separate resolve_variable() call and string replacement

**Scale limits**:
- Handles 100s of variables easily
- Prompts with 1000s of variables (unlikely) may see overhead
- Not a v0.1 blocker (typical prompts 200-500 chars, 5-20 variables)

**Fix approach** (if needed):
1. Build single substitution dict before replacements
2. Use regex-based single-pass replacement
3. Benchmark before/after on realistic prompts
4. Estimated effort: 2-3 hours
5. Priority: Low (not blocking, only for extreme cases)

---

### MLFlow Observability Overhead

**Issue**: MLFlow 3.9 integration adds instrumentation overhead

**Files**:
- `src/configurable_agents/observability/mlflow_tracker.py` (initialization)
- `src/configurable_agents/runtime/executor.py` (tracker creation)
- ADR-018 documents MLFlow 3.9 migration

**Current state**: MLFlow 3.9 auto-instrumentation via mlflow.langchain.autolog()

**Impact**:
- Each LLM call traced automatically (slight overhead)
- Cost calculation post-processing adds 5-10ms per trace
- File-based backend (local) fast; remote servers slower

**Mitigation**:
- ✅ Auto-instrumentation disabled when mlflow_config.enabled=False
- ✅ Graceful degradation if MLFlow server unavailable
- ✅ File-based backend default for local development

**Known limitation**: Remote MLFlow tracking to slow servers will impact latency. Use file-based backend locally, upgrade to remote (Databricks, AWS) for production.

**Fix approach** (if needed):
1. Add MLFlow server performance profiling
2. Consider caching trace data before flush
3. Make trace recording async (v0.2+)
4. Estimated effort: 1-2 days
5. Priority: Low (not blocking for local development)

---

## Scaling Limits

### In-Memory State Scale

**Issue**: State size limited by available RAM

**Constraint**: ADR-008 specifies in-memory state only

**Current capacity**:
- Typical workflow state: 1-100 MB (articles, research summaries)
- RAM available: Depends on deployment (local: 8GB+, containers: 512MB-4GB)
- Theoretical limit: ~80% of available RAM

**Scaling path** (v0.2+):
1. File-based checkpointing (current disk available)
2. Database persistence (query historical runs)
3. Redis/distributed state (share across workers)

**Workaround for v0.1**: Compress state between nodes if exceeding limits (not recommended)

---

### LLM Context Window Accumulation

**Issue**: Prompt context builds across nodes without trimming

**Files**: `src/configurable_agents/core/node_executor.py:execute_node()` (prompt resolution)

**Problem**:
- Each node references prior state: {research}, {outline}, {draft}
- State grows with each node execution
- Prompts can exceed LLM context limits for long workflows

**Scale limits**:
- Google Gemini: 32K tokens (v0.1)
- Typical: 50+ nodes × 500 tokens per prompt = 25K tokens
- Beyond that: Context overflow errors

**Known limitation**: This is v0.1 design (linear workflows, simple state)

**Fix approach** (v0.2+):
1. Add optional context trimming rules
2. Implement state summarization between nodes
3. Support streaming for long outputs
4. Estimated effort: 2-3 days

---

### Tool Registry Scale

**Issue**: Tool registry limited to registered tools

**Files**: `src/configurable_agents/tools/registry.py:63-68` (_register_builtin_tools)

**Current**: Only serper_search built-in

**Scale**:
- 1-5 tools easily manageable
- Adding 50+ tools requires organization (namespacing, lazy loading)

**Known limitation**: Deliberate v0.1 constraint (one tool as MVP)

**Fix approach** (v0.2+):
1. Implement tool discovery from plugins directory
2. Support tool versioning and dependencies
3. Add tool search/discovery command
4. Estimated effort: 2-3 days

---

## Dependencies at Risk

### MLFlow Version Upgrade (Recent)

**Issue**: Migration from MLFlow 2.9 to 3.9 completed (T-028)

**Files**:
- `pyproject.toml:33` (mlflow>=3.9.0)
- `src/configurable_agents/observability/mlflow_tracker.py` (new implementation)
- ADR-018 documents migration decision

**Risk**:
- ⚠️ Recently migrated (Feb 2026) - potential instability
- ⚠️ GenAI features relatively new in MLFlow
- ⚠️ Auto-instrumentation behavior may change in 3.10+

**Mitigation**:
- ✅ MLFlow optional (graceful degradation if not installed)
- ✅ Autolog wrapped in try/except with logging
- ✅ Tests mock MLFlow to avoid dependency on its stability

**Recommendations**:
1. Pin mlflow>=3.9.0, <4.0.0 to avoid breaking changes (consider in pyproject.toml)
2. Monitor MLFlow 4.0 release notes for compatibility
3. Keep migration notes (ADR-018) for reference
4. Add MLFlow version check in CLI output (--version flag)

---

### LangChain Ecosystem Dependency

**Issue**: Heavy dependence on LangChain libraries

**Files**:
- `pyproject.toml:29-31` (langchain, langchain-community, langchain-google-genai)
- Multiple imports across core modules

**Risk**:
- ⚠️ LangChain API changes frequently (major versions)
- ⚠️ Heavy abstraction may hide breaking changes
- ⚠️ Community tools can be unstable

**Mitigation**:
- ✅ Using stable versions (langchain>=0.1.0)
- ✅ Dependency abstraction (tools/registry.py, llm/provider.py)
- ✅ Core logic independent of LangChain patterns

**Known dependency**: LangGraph is core execution engine (ADR-001). Can't remove, but abstracted well.

**Recommendations**:
1. Monitor LangChain 0.2+ release notes
2. Version-lock for stability: consider langchain>=0.1.0,<0.3.0
3. Gradual upgrade path when 1.0 released
4. Test integration regularly (CI should catch breaks)

---

### Pydantic V2 Strict Mode

**Issue**: Using Pydantic 2.0+ strict typing

**Files**:
- `pyproject.toml:26` (pydantic>=2.0)
- Config throughout: `StateFieldConfig`, `NodeConfig`, etc.
- ADR-002 documents strict typing decision

**Risk**:
- ⚠️ Type coercion might be too strict in edge cases
- ⚠️ Nested object validation complex
- ⚠️ Future Pydantic 3.0 may change validation rules

**Mitigation**:
- ✅ Full schema tested (ADR-009 - full schema day one)
- ✅ 645 passing tests provide regression detection
- ✅ Validation errors have good hints

**Known dependency**: Pydantic 2.0 chosen for excellent error messages (design decision, not risk).

**Recommendations**:
1. Keep pydantic>=2.0,<3.0 constraint in pyproject.toml
2. Monitor Pydantic 3.0 roadmap (beta may be coming 2026-2027)
3. Plan migration if 3.0 introduces breaking changes
4. Test with latest 2.x version periodically

---

## Missing Critical Features

### Feature Gate Warnings Not Prominently Displayed

**Issue**: Future features (v0.2, v0.3) generate warnings not always seen

**Files**: `src/configurable_agents/runtime/feature_gate.py:15-120` (validate_runtime_support)

**Impact**:
- Users may define workflows expecting v0.2 features thinking they'll work
- Warnings logged to debug/info level, might be missed
- No explicit error list in config validation output

**Workaround**: Feature gate works correctly (raises errors), but warning visibility could be better

**Fix approach**:
1. Add explicit feature summary to validation output
2. Print unsupported features warning in CLI (not just logs)
3. Consider --strict flag to error on unsupported features
4. Estimated effort: 2-3 hours

---

### Cost Estimation Accuracy

**Issue**: Cost calculation uses estimates, not actual token counts

**Files**:
- `src/configurable_agents/observability/cost_estimator.py` (token estimation)
- `src/configurable_agents/observability/cost_reporter.py` (cost reporting)

**Impact**:
- Reported costs may differ from actual billed costs
- LLM providers (Google, OpenAI) have different pricing models
- v0.1 only supports Google Gemini (hardcoded costs)

**Known limitation**: Cost estimates documented as "estimated" in reports

**Accuracy**:
- ✅ For Gemini: accurate for input/output token counts
- ❌ Actual LLM pricing tier ($0.075 vs $0.15 per 1M input tokens) not reflected
- ❌ No support for other providers (OpenAI, Anthropic have different rates)

**Fix approach** (v0.2+):
1. Make pricing configurable per provider
2. Use actual token counts from LLM responses (available in API responses)
3. Support multiple providers with different rate cards
4. Estimated effort: 1-2 days

---

## Error Message Quality

### Validator Similarity Suggestions

**Issue**: Helpful but may not always match user intent

**Files**: `src/configurable_agents/config/validator.py:43-80` (_find_similar, edit_distance)

**Example**:
```
Error: "Node 'write' references unknown state field 'artcile'. Did you mean 'article'?"
```

**Impact**:
- Very helpful for typos
- Might be confusing for intentional differences
- Edit distance threshold (2) arbitrary

**Mitigation**:
- ✅ Suggestions are optional ("Did you mean...?")
- ✅ Obvious errors for complete mismatches
- ✅ Users can ignore suggestions and check intentionally

**Safe modification**: Threshold is reasonable for typical YAML lengths. No change needed unless complaints arise.

---

## Unused/Stub Code

### Exception Class Definitions

**Issue**: Some exception classes defined but not actively used

**Files**: Check for unused exception classes in:
- `src/configurable_agents/config/validator.py` (ValidationError - used)
- `src/configurable_agents/core/node_executor.py` (NodeExecutionError - used)
- `src/configurable_agents/runtime/executor.py` (ExecutionError and subclasses - used)

**Status**: All exception classes actively used. No stubs found.

---

## Documentation Gaps

### CONTRIBUTING.md Missing

**Issue**: No contribution guidelines documented

**Files**: None yet - would be `CONTRIBUTING.md`

**Impact**:
- Unclear how to add tools, providers, validators
- Extension points exist (ARCHITECTURE.md documents them) but could be clearer
- Test setup not documented for external contributors

**Fix approach**:
1. Create CONTRIBUTING.md with:
   - Setup instructions for development
   - How to add tools (step-by-step)
   - How to add LLM providers
   - How to add validation rules
   - Testing requirements (coverage target)
2. Reference from README.md
3. Estimated effort: 2-3 hours

---

### Troubleshooting Guide Incomplete

**Issue**: TROUBLESHOOTING.md exists but may be outdated

**Files**: `docs/TROUBLESHOOTING.md` (may need review)

**Impact**:
- Common issues not documented
- Users may struggle with setup or deployment

**Known issues to document**:
- API key configuration (SERPER_API_KEY, GOOGLE_API_KEY)
- MLFlow server connection issues
- Docker deployment errors
- Template resolution failures

**Fix approach**:
1. Audit common error messages in code
2. Add troubleshooting entries for top 10 issues
3. Include solution steps and links to documentation
4. Estimated effort: 2-4 hours

---

## Known Bugs

### None Currently Identified

**Status**: All identified issues are either:
- Design constraints (in-memory state, single LLM provider)
- Tech debt (template resolver workaround)
- Potential improvements (error context, scaling)

No active bugs reported in issue tracker or code comments.

---

## Summary by Priority

### High Priority (Blocks Production Use)

1. **State Persistence Gap**: Document workaround for short-lived workflows; plan v0.2 persistence
2. **Template Resolver TODO**: Fix {state.X} syntax preprocessing
3. **Error Context**: Improve error messages in node execution failures

### Medium Priority (Improves Stability)

1. **Integration Test Coverage**: Expand error scenario testing
2. **Feature Gate Visibility**: Make unsupported features more obvious
3. **MLFlow Version Pinning**: Lock MLFlow to avoid breaking changes

### Low Priority (Technical Improvement)

1. **CLI Module Size**: Acceptable for v0.1; refactor if adding many new commands
2. **Template Performance**: Not a bottleneck for realistic workflows
3. **Cost Estimation Accuracy**: Acceptable estimates; improve in multi-provider support
4. **CONTRIBUTING.md**: Nice-to-have documentation

---

*Concerns audit: 2026-02-02*
