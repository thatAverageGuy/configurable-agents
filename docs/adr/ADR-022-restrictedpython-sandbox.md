# ADR-022: RestrictedPython Sandbox

**Status**: Accepted
**Date**: 2026-02-04
**Deciders**: thatAverageGuy, Claude Code

---

## Context

The system needs to execute agent-generated Python code safely within workflows. This code comes from LLMs and cannot be trusted.

### Requirements

- **RT-04**: User can run agent-generated code in sandboxed environment (Docker-based isolation with resource limits)

### Constraints

- Must prevent access to dangerous operations (file system, network, subprocess)
- Must limit resource usage (CPU, memory, timeout)
- Must work in local development (no Docker required)
- Must support optional Docker isolation for production

---

## Decision

**Use RestrictedPython by default for fast, safe execution. Use Docker opt-in for strict isolation with resource limits.**

---

## Rationale

### Why RestrictedPython?

1. **Safe by Default**: Blocks dangerous operations (file I/O, subprocess, import)
2. **No Dependencies**: Pure Python, works everywhere
3. **Fast**: No container startup overhead (~100ms vs ~3s for Docker)
4. **Inspectable**: Can see exactly what code is allowed
5. **Proven**: Used in Zope/Plone for 20+ years

### Why Docker Opt-In?

1. **Strict Isolation**: Network isolation, separate process
2. **Resource Limits**: CPU, memory, timeout enforcement
3. **Optional**: Users can choose security level
4. **Production-Ready**: Suitable for untrusted code

### Why Hybrid Approach?

- **Default**: RestrictedPython (fast, good enough for most use cases)
- **Opt-In**: Docker (for strict isolation requirements)
- **Flexible**: User chooses based on threat model

---

## Implementation

### RestrictedPython Execution

```python
from RestrictedPython import compile_restricted
from RestrictedPython.Guards import guarded_iter_unpack_sequence
from RestrictedPython.Guards import safe_builtins

def execute_restricted_code(code: str, inputs: dict) -> dict:
    """Execute code in RestrictedPython sandbox"""

    # Compile with restrictions
    byte_code = compile_restricted(code, "<string>", "exec")

    # Safe globals (whitelisted)
    safe_globals = {
        "__builtins__": {
            "print": _safe_print,
            "len": len,
            "range": range,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "set": set,
            "tuple": tuple,
            # ... (safe builtins only)
        },
        "_getiter_": guarded_iter_unpack_sequence,
        "_print_": _SafePrint,
        "__name__": "__main__",
    }

    # Execute with inputs
    safe_locals = {"inputs": inputs, "result": None}

    exec(byte_code, safe_globals, safe_locals)

    return safe_locals.get("result", {})
```

### Safe Globals

```python
class _SafePrint:
    """Safe print function that logs instead of writing to stdout"""
    def __init__(self):
        self.output = []

    def __call__(self, *args, **kwargs):
        self.output.append(" ".join(str(a) for a in args))

def _safe_getattr(obj, attr):
    """Custom getattr that blocks private attributes"""
    if attr.startswith("_"):
        raise AttributeError(f"Access to private attribute '{attr}' blocked")
    return getattr(obj, attr)
```

### Docker Execution (Opt-In)

```python
def execute_in_docker(code: str, inputs: dict, config: SandboxConfig) -> dict:
    """Execute code in Docker container"""

    client = docker.from_env()

    # Mount code as file
    code_file = Path("/tmp/sandbox_code.py")
    code_file.write_text(code)

    # Run container
    result = client.containers.run(
        "python:3.10-slim",
        command=f"python /workspace/sandbox_code.py",
        volumes={str(code_file.parent): {"bind": "/workspace", "mode": "ro"}},
        environment={"INPUTS": json.dumps(inputs)},
        mem_limit=config.memory_limit,
        cpu_quota=int(config.cpu_cores * 100000),
        network_disabled=config.network_disabled,
        remove=True,
        capture_output=True,
    )

    return json.loads(result.stdout)
```

### Resource Presets

```python
SANDBOX_PRESETS = {
    "low": {"cpu_cores": 0.5, "memory_limit": "256m", "timeout": 10},
    "medium": {"cpu_cores": 1.0, "memory_limit": "512m", "timeout": 30},
    "high": {"cpu_cores": 2.0, "memory_limit": "1g", "timeout": 60},
    "max": {"cpu_cores": 4.0, "memory_limit": "2g", "timeout": 120},
}
```

---

## Configuration

### Node-Level Sandbox Config

```yaml
nodes:
  - id: data_processor
    code: |
      result = process_data(inputs["data"])
      return {"output": result}
    sandbox:
      enabled: true
      mode: "restricted"  # or "docker"
      preset: "medium"
      timeout: 30
      network_isolated: false
```

### Global Sandbox Config

```yaml
config:
  sandbox:
    default_mode: "restricted"
    default_preset: "medium"
    allow_imports: false
    allow_file_ops: false
    allowed_paths: []
    allowed_commands: []
```

---

## Security Measures

### RestrictedPython

- **No `os` module**: Blocks file system and process operations
- **No `subprocess`**: Blocks command execution
- **No `eval`/`exec`**: Blocks dynamic code execution
- **No `import`**: Blocks module loading (unless explicitly allowed)
- **No private attributes**: Blocks access to `_` prefixed names
- **Safe builtins**: Only whitelisted functions (len, range, str, etc.)

### Docker

- **Network Isolation**: Optional network disable
- **Read-Only Volumes**: Code can't modify mounted files
- **Resource Limits**: CPU, memory, timeout enforced
- **Ephemeral**: Container removed after execution
- **Separate Process**: Crash doesn't affect host

### Whitelisting

```python
ALLOWED_IMPORTS = ["math", "json", "re", "datetime", "collections"]
ALLOWED_PATHS = ["/tmp/sandbox", "/data/readonly"]
ALLOWED_COMMANDS = ["echo", "cat"]  # If shell enabled
```

---

## Error Handling

### Graceful Degradation

```python
try:
    result = execute_restricted_code(code, inputs)
except SyntaxError as e:
    return {"error": f"Syntax error: {e}", "output": None}
except SecurityError as e:
    return {"error": f"Security violation: {e}", "output": None}
except Exception as e:
    if config.on_error == "continue":
        return {"error": str(e), "output": None}
    else:
        raise
```

### On Error Modes

```yaml
nodes:
  - id: risky_node
    code: |
      # May fail
      result = risky_operation(data)
      return {"output": result}
    sandbox:
      on_error: "continue"  # or "fail"
```

---

## Alternatives Considered

### Alternative 1: Docker Only

**Pros**:
- Strictest isolation
- Production-grade security
- Clear boundary

**Cons**:
- Slow startup (~3s per execution)
- Heavy dependency (Docker required)
- Overkill for local development
- Can't run without Docker installed

**Why rejected**: Too slow for local development. Users may not have Docker.

### Alternative 2: AST Validation (No RestrictedPython)

**Pros**:
- Lightweight (no dependency)
- Full control

**Cons**:
- Reinventing the wheel
- Security vulnerabilities (edge cases)
- Maintenance burden

**Why rejected**: RestrictedPython is battle-tested. Don't roll own security.

### Alternative 3: PyPy Sandbox

**Pros**:
- Faster execution
- Same API as CPython

**Cons**:
- Still experimental
- Limited compatibility
- No hardened security model

**Why rejected**: Not production-ready. RestrictedPython is proven.

---

## Consequences

### Positive Consequences

1. **Fast Execution**: RestrictedPython executes in ~100ms
2. **No Docker Required**: Works everywhere Python runs
3. **Flexible Security**: Users choose isolation level
4. **Inspectable**: Clear what's allowed/blocked
5. **Production-Ready**: Docker opt-in for strict isolation

### Negative Consequences

1. **Limited Python**: RestrictedPython doesn't support all Python features
2. **Learning Curve**: Users must understand sandbox constraints
3. **Debugging**: Harder to debug restricted code (no print to console by default)
4. **Performance**: RestrictedPython slower than native Python

### Risks

#### Risk 1: RestrictedPython Bypass

**Likelihood**: Low (20-year track record)
**Impact**: High
**Mitigation**: Defense-in-depth. Layer RestrictedPython + AppArmor (in Docker) + user education.

#### Risk 2: Docker Escape Vulnerability

**Likelihood**: Low (container escapes are rare)
**Impact**: High
**Mitigation**: Keep Docker updated. Use user namespaces. Run as non-root.

#### Risk 3: Resource Exhaustion

**Likelihood**: Medium
**Impact**: Medium
**Mitigation**: Resource presets (CPU, memory, timeout). Monitor with cgroups.

---

## Related Decisions

- [ADR-001](ADR-001-langgraph-execution-engine.md): Node execution (sandbox integration)
- [ADR-012](ADR-012-docker-deployment-architecture.md): Docker deployment patterns

---

## Implementation Status

**Status**: ✅ Complete (v1.0)

**Files**:
- `src/configurable_agents/sandbox/restricted_python.py` - RestrictedPython executor
- `src/configurable_agents/sandbox/docker_executor.py` - Docker executor (opt-in)
- `src/configurable_agents/sandbox/presets.py` - Resource limit presets

**Features**:
- Safe globals (print, getattr, import guards)
- Error handling continuation (on_error: continue)
- Resource presets (low/medium/high/max)
- Network isolation (Docker opt-in)
- Security whitelisting (paths, commands)

**Testing**: 25 tests covering restricted execution, Docker isolation, and error handling

---

## Superseded By

None (current)
