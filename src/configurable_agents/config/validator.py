"""
Config validation beyond Pydantic schema validation.

Performs cross-reference validation, graph validation, and v0.1 constraint checks.
Fail-fast strategy: stops at first error category with helpful suggestions.
"""

import re
from collections import defaultdict, deque
from typing import Dict, List, Optional, Set

from configurable_agents.config.schema import WorkflowConfig
from configurable_agents.config.types import TypeParseError, validate_type_string


class ValidationError(Exception):
    """
    Raised when config validation fails.

    Includes helpful error message with context and suggestions.
    """

    def __init__(
        self,
        message: str,
        suggestion: Optional[str] = None,
        context: Optional[str] = None,
    ):
        self.message = message
        self.suggestion = suggestion
        self.context = context

        # Build full error message
        parts = [message]
        if context:
            parts.append(f"\nContext: {context}")
        if suggestion:
            parts.append(f"\nSuggestion: {suggestion}")

        super().__init__("\n".join(parts))


def _find_similar(target: str, candidates: List[str], threshold: int = 2) -> Optional[str]:
    """
    Find similar string using simple edit distance.

    Args:
        target: String to match
        candidates: List of candidates
        threshold: Max edit distance to consider a match

    Returns:
        Most similar candidate, or None if no good match
    """
    def edit_distance(s1: str, s2: str) -> int:
        """Calculate Levenshtein distance."""
        if len(s1) < len(s2):
            return edit_distance(s2, s1)
        if len(s2) == 0:
            return len(s1)

        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row

        return previous_row[-1]

    best_match = None
    best_distance = threshold + 1

    for candidate in candidates:
        distance = edit_distance(target.lower(), candidate.lower())
        if distance < best_distance:
            best_distance = distance
            best_match = candidate

    return best_match if best_distance <= threshold else None


def _extract_placeholders(template: str) -> Set[str]:
    """
    Extract {placeholder} references from template string.

    Args:
        template: Template string with {var} placeholders

    Returns:
        Set of placeholder names (without braces)
    """
    # Match {variable} or {state.field} patterns
    pattern = r"\{([^}]+)\}"
    matches = re.findall(pattern, template)
    return set(matches)


def validate_config(config: WorkflowConfig) -> None:
    """
    Validate workflow config beyond Pydantic schema validation.

    Performs:
    - Node/edge reference validation
    - State field cross-references
    - Type alignment checks
    - Graph connectivity validation
    - Linear flow enforcement (v0.1)

    Args:
        config: Workflow configuration to validate

    Raises:
        ValidationError: If validation fails (fail-fast)
    """
    # Build indices for fast lookup
    node_ids = {node.id for node in config.nodes}
    state_fields = set(config.state.fields.keys())

    # 1. Validate node references in edges
    _validate_edge_references(config, node_ids)

    # 2. Validate node outputs reference valid state fields
    _validate_node_outputs(config, state_fields)

    # 3. Validate output schema fields match outputs list
    _validate_output_schema_alignment(config)

    # 4. Validate output types match state types
    _validate_output_type_alignment(config)

    # 5. Validate prompt placeholders
    _validate_prompt_placeholders(config, state_fields)

    # 6. Validate state field types are valid
    _validate_state_types(config)

    # 7. Validate linear flow constraints (v0.1) - check before graph structure
    # This catches cycles and multiple edges which would cause graph structure failures
    _validate_linear_flow(config, node_ids)

    # 8. Validate graph structure (connectivity, reachability)
    _validate_graph_structure(config, node_ids)


def _validate_edge_references(config: WorkflowConfig, node_ids: Set[str]) -> None:
    """Validate that all edge references point to valid nodes or START/END."""
    valid_nodes = node_ids | {"START", "END"}

    for i, edge in enumerate(config.edges):
        # Validate 'from'
        if edge.from_ not in valid_nodes:
            similar = _find_similar(edge.from_, list(valid_nodes))
            suggestion = f"Did you mean '{similar}'?" if similar else f"Valid nodes: {sorted(valid_nodes)}"
            raise ValidationError(
                f"Edge {i}: 'from' references unknown node '{edge.from_}'",
                suggestion=suggestion,
                context=f"Edge: {edge.from_} -> {edge.to or 'routes'}",
            )

        # Validate 'to' (if linear edge)
        if edge.to:
            if edge.to not in valid_nodes:
                similar = _find_similar(edge.to, list(valid_nodes))
                suggestion = f"Did you mean '{similar}'?" if similar else f"Valid nodes: {sorted(valid_nodes)}"
                raise ValidationError(
                    f"Edge {i}: 'to' references unknown node '{edge.to}'",
                    suggestion=suggestion,
                    context=f"Edge: {edge.from_} -> {edge.to}",
                )

        # Validate 'routes' (if conditional edge)
        if edge.routes:
            for route in edge.routes:
                if route.to not in valid_nodes:
                    similar = _find_similar(route.to, list(valid_nodes))
                    suggestion = f"Did you mean '{similar}'?" if similar else f"Valid nodes: {sorted(valid_nodes)}"
                    raise ValidationError(
                        f"Edge {i}: route references unknown node '{route.to}'",
                        suggestion=suggestion,
                        context=f"Edge: {edge.from_} -> routes",
                    )


def _validate_node_outputs(config: WorkflowConfig, state_fields: Set[str]) -> None:
    """Validate that node outputs reference valid state fields."""
    for node in config.nodes:
        for output in node.outputs:
            if output not in state_fields:
                similar = _find_similar(output, list(state_fields))
                suggestion = (
                    f"Did you mean '{similar}'?"
                    if similar
                    else f"Add '{output}' to state.fields or check spelling. Available fields: {sorted(state_fields)}"
                )
                raise ValidationError(
                    f"Node '{node.id}': output '{output}' not found in state fields",
                    suggestion=suggestion,
                    context=f"Node outputs: {node.outputs}",
                )


def _validate_output_schema_alignment(config: WorkflowConfig) -> None:
    """Validate that output_schema fields match the outputs list."""
    for node in config.nodes:
        # For object output schemas, check field names
        if node.output_schema.type == "object":
            if not node.output_schema.fields:
                raise ValidationError(
                    f"Node '{node.id}': output_schema type='object' but no fields defined",
                    suggestion="Add fields to output_schema or change type to a basic type (str, int, etc.)",
                    context=f"Node: {node.id}",
                )

            schema_field_names = {f.name for f in node.output_schema.fields}
            output_names = set(node.outputs)

            # Check that all outputs are in schema
            missing_in_schema = output_names - schema_field_names
            if missing_in_schema:
                raise ValidationError(
                    f"Node '{node.id}': outputs {sorted(missing_in_schema)} not defined in output_schema.fields",
                    suggestion=f"Add these fields to output_schema: {sorted(missing_in_schema)}",
                    context=f"Outputs: {node.outputs}, Schema fields: {sorted(schema_field_names)}",
                )

            # Check that all schema fields are in outputs
            extra_in_schema = schema_field_names - output_names
            if extra_in_schema:
                raise ValidationError(
                    f"Node '{node.id}': output_schema defines fields {sorted(extra_in_schema)} but they're not in outputs",
                    suggestion=f"Add these to outputs list or remove from output_schema: {sorted(extra_in_schema)}",
                    context=f"Outputs: {node.outputs}, Schema fields: {sorted(schema_field_names)}",
                )

        # For simple output schemas, check single output
        else:
            if len(node.outputs) != 1:
                raise ValidationError(
                    f"Node '{node.id}': output_schema type='{node.output_schema.type}' (simple type) but outputs list has {len(node.outputs)} items",
                    suggestion=f"Either change output_schema.type to 'object' with multiple fields, or use single output",
                    context=f"Outputs: {node.outputs}",
                )


def _validate_output_type_alignment(config: WorkflowConfig) -> None:
    """Validate that output types in schema match state field types."""
    state_types = {name: field.type for name, field in config.state.fields.items()}

    for node in config.nodes:
        if node.output_schema.type == "object" and node.output_schema.fields:
            for field in node.output_schema.fields:
                if field.name in state_types:
                    state_type = state_types[field.name]
                    schema_type = field.type

                    if state_type != schema_type:
                        raise ValidationError(
                            f"Node '{node.id}': output field '{field.name}' has type '{schema_type}' "
                            f"but state field has type '{state_type}'",
                            suggestion=f"Change output_schema field type to '{state_type}' or update state field type",
                            context=f"State: {field.name}: {state_type}, Output schema: {field.name}: {schema_type}",
                        )
        else:
            # Simple type output
            output_name = node.outputs[0]
            if output_name in state_types:
                state_type = state_types[output_name]
                schema_type = node.output_schema.type

                if state_type != schema_type:
                    raise ValidationError(
                        f"Node '{node.id}': output '{output_name}' has type '{schema_type}' "
                        f"but state field has type '{state_type}'",
                        suggestion=f"Change output_schema.type to '{state_type}' or update state field type",
                        context=f"State: {output_name}: {state_type}, Output schema: {schema_type}",
                    )


def _validate_prompt_placeholders(config: WorkflowConfig, state_fields: Set[str]) -> None:
    """Validate that prompt placeholders reference valid state fields or inputs."""
    for node in config.nodes:
        placeholders = _extract_placeholders(node.prompt)

        # Build valid references: state fields + input mappings
        valid_refs = state_fields.copy()
        if node.inputs:
            valid_refs.update(node.inputs.keys())

        for placeholder in placeholders:
            # Handle nested references like "state.field" or just "field"
            parts = placeholder.split(".")
            base_ref = parts[0]

            # Skip "state." prefix if present
            if base_ref == "state" and len(parts) > 1:
                field_name = parts[1]
                if field_name not in state_fields:
                    similar = _find_similar(field_name, list(state_fields))
                    suggestion = (
                        f"Did you mean '{{state.{similar}}}'?"
                        if similar
                        else f"Available state fields: {sorted(state_fields)}"
                    )
                    raise ValidationError(
                        f"Node '{node.id}': prompt placeholder '{{state.{field_name}}}' references unknown state field",
                        suggestion=suggestion,
                        context=f"Prompt: {node.prompt[:100]}...",
                    )
            else:
                # Direct reference (not state.field)
                if base_ref not in valid_refs:
                    similar = _find_similar(base_ref, list(valid_refs))
                    suggestion = (
                        f"Did you mean '{{{similar}}}'?"
                        if similar
                        else f"Available: {sorted(valid_refs)}"
                    )
                    raise ValidationError(
                        f"Node '{node.id}': prompt placeholder '{{{placeholder}}}' not found",
                        suggestion=suggestion,
                        context=f"Prompt: {node.prompt[:100]}...",
                    )


def _validate_state_types(config: WorkflowConfig) -> None:
    """Validate that all state field types are valid type strings."""
    for field_name, field_config in config.state.fields.items():
        try:
            # Validate type string parses correctly
            if not validate_type_string(field_config.type):
                raise ValidationError(
                    f"State field '{field_name}': invalid type '{field_config.type}'",
                    suggestion="Use supported types: str, int, float, bool, list, dict, list[T], dict[K,V], object",
                )
        except TypeParseError as e:
            raise ValidationError(
                f"State field '{field_name}': {str(e)}",
                suggestion="Use supported types: str, int, float, bool, list, dict, list[T], dict[K,V], object",
            )


def _validate_graph_structure(config: WorkflowConfig, node_ids: Set[str]) -> None:
    """
    Validate graph structure and connectivity.

    Checks:
    - Exactly one edge from START
    - All nodes reachable from START
    - All nodes have path to END
    - No orphaned nodes
    """
    # Build adjacency list
    graph: Dict[str, Set[str]] = defaultdict(set)
    reverse_graph: Dict[str, Set[str]] = defaultdict(set)

    for edge in config.edges:
        if edge.to:
            # Linear edge
            graph[edge.from_].add(edge.to)
            reverse_graph[edge.to].add(edge.from_)
        elif edge.routes:
            # Conditional routes
            for route in edge.routes:
                graph[edge.from_].add(route.to)
                reverse_graph[route.to].add(edge.from_)

    # 1. Check exactly one edge from START
    start_edges = graph.get("START", set())
    if len(start_edges) == 0:
        raise ValidationError(
            "No edge from START node",
            suggestion="Add an edge with from='START' to your first node",
            context=f"Available nodes: {sorted(node_ids)}",
        )
    if len(start_edges) > 1:
        raise ValidationError(
            f"Multiple edges from START: {sorted(start_edges)}",
            suggestion="START should have exactly one outgoing edge",
            context="Linear workflows must have a single entry point",
        )

    # 2. Check all nodes reachable from START (forward BFS)
    reachable = _bfs(graph, "START")
    reachable.discard("START")
    reachable.discard("END")

    unreachable = node_ids - reachable
    if unreachable:
        raise ValidationError(
            f"Nodes not reachable from START: {sorted(unreachable)}",
            suggestion="Add edges to connect these nodes to the workflow, or remove them",
            context="All nodes must be reachable from START",
        )

    # 3. Check all nodes have path to END (backward BFS)
    can_reach_end = _bfs(reverse_graph, "END")
    can_reach_end.discard("START")
    can_reach_end.discard("END")

    cannot_reach_end = node_ids - can_reach_end
    if cannot_reach_end:
        raise ValidationError(
            f"Nodes cannot reach END: {sorted(cannot_reach_end)}",
            suggestion="Add edges from these nodes to END, or connect them to nodes that reach END",
            context="All nodes must have a path to END",
        )


def _validate_linear_flow(config: WorkflowConfig, node_ids: Set[str]) -> None:
    """
    Validate v0.1 linear flow constraints.

    Checks:
    - No conditional routing (routes)
    - No cycles in the graph
    - Each node has at most one outgoing edge
    """
    # 1. Check for conditional routing
    for i, edge in enumerate(config.edges):
        if edge.routes:
            raise ValidationError(
                f"Edge {i}: Conditional routing not supported in v0.1",
                suggestion="Use linear edges (from/to) instead. Conditional routing available in v0.2+ (8-12 weeks)",
                context=f"Edge: {edge.from_} -> routes. See docs/PROJECT_VISION.md for roadmap",
            )

    # 2. Check each node has at most one outgoing edge
    outgoing_counts: Dict[str, int] = defaultdict(int)
    for edge in config.edges:
        outgoing_counts[edge.from_] += 1

    for node, count in outgoing_counts.items():
        if node != "START" and count > 1:
            raise ValidationError(
                f"Node '{node}' has {count} outgoing edges",
                suggestion="v0.1 supports linear flows only. Each node should have 0-1 outgoing edges",
                context="Multiple outgoing edges require conditional routing (v0.2+)",
            )

    # 3. Check for cycles using DFS
    graph: Dict[str, str] = {}
    for edge in config.edges:
        if edge.to:
            graph[edge.from_] = edge.to

    visited: Set[str] = set()
    rec_stack: Set[str] = set()

    def has_cycle(node: str, path: List[str]) -> Optional[List[str]]:
        """DFS to detect cycles. Returns cycle path if found."""
        if node in rec_stack:
            # Found cycle - extract cycle path
            cycle_start = path.index(node)
            return path[cycle_start:] + [node]

        if node in visited:
            return None

        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        # Visit next node
        if node in graph:
            next_node = graph[node]
            cycle = has_cycle(next_node, path)
            if cycle:
                return cycle

        path.pop()
        rec_stack.remove(node)
        return None

    # Check from START
    cycle = has_cycle("START", [])
    if cycle:
        cycle_str = " -> ".join(cycle)
        raise ValidationError(
            f"Cycle detected in workflow: {cycle_str}",
            suggestion="Remove edges to break the cycle. Linear workflows cannot have loops (loops available in v0.2+)",
            context="v0.1 supports linear flows only",
        )


def _bfs(graph: Dict[str, Set[str]], start: str) -> Set[str]:
    """
    Breadth-first search to find all reachable nodes.

    Args:
        graph: Adjacency list
        start: Starting node

    Returns:
        Set of reachable nodes (including start)
    """
    visited = {start}
    queue = deque([start])

    while queue:
        node = queue.popleft()
        for neighbor in graph.get(node, set()):
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    return visited
