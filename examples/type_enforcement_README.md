# Type Enforcement Demo

**File**: `type_enforcement.yaml`
**Complexity**: ⭐⭐⭐ Advanced (comprehensive type coverage)

## What It Does

A comprehensive demonstration of type enforcement across all supported types:
- Simple types: `str`, `int`, `bool`, `float`
- Collection types: `list[str]`, `dict[str, int]`
- Complex objects with nested structures

This example shows how the system ensures LLMs return correctly-typed data.

Perfect for understanding:
- Type system capabilities
- How type enforcement prevents errors
- Structured output validation
- Multiple output types in single node
- Automatic retry on type mismatches

## Structure

- **1 input**: `topic` (str)
- **6 outputs**: Demonstrating all major type categories
- **1 node**: Produces multiple typed outputs simultaneously
- **Type enforcement**: Pydantic validation on all outputs

## Supported Types Demonstrated

| Type | Example | Purpose |
|------|---------|---------|
| `int` | `score: 85` | Whole numbers |
| `bool` | `is_trending: true` | True/false flags |
| `list[str]` | `keywords: ["AI", "ML"]` | Lists of strings |
| `dict[str, int]` | `categories: {"tech": 95}` | Key-value mappings |
| `object` | Nested structure | Complex nested data |
| `float` | `confidence: 0.87` | Decimal numbers |

## Usage

### CLI

```bash
configurable-agents run type_enforcement.yaml --input topic="Artificial Intelligence"
```

### Python

```python
from configurable_agents.runtime import run_workflow

result = run_workflow(
    "examples/type_enforcement.yaml",
    {"topic": "Artificial Intelligence"}
)

print(f"Score: {result['score']} (type: {type(result['score']).__name__})")
print(f"Trending: {result['is_trending']} (type: {type(result['is_trending']).__name__})")
print(f"Keywords: {result['keywords']}")
print(f"Categories: {result['categories']}")
print(f"Analysis: {result['analysis']}")
```

## Expected Output

```
Result:
  topic: Artificial Intelligence
  score: 92  # <-- Integer (not float, not string)
  is_trending: true  # <-- Boolean (not string "true")
  keywords:  # <-- List of strings
    - artificial intelligence
    - machine learning
    - neural networks
    - deep learning
    - automation
    - AI ethics
  categories:  # <-- Dict with string keys, int values
    Technology: 95
    Science: 88
    Business: 76
    Education: 82
    Healthcare: 73
  analysis:  # <-- Nested object
    summary: |
      Artificial intelligence represents a transformative technology
      reshaping multiple industries. Growing rapidly with increasing
      investment and public interest.
    sentiment: positive
    confidence: 0.89  # <-- Float (not integer)
    tags:
      - transformative
      - rapidly-growing
      - multi-industry
      - high-investment
```

## Type Enforcement in Action

### What Happens When Types Are Wrong?

The system automatically detects and corrects type mismatches:

**Scenario 1: LLM returns string instead of int**
```json
{"score": "85"}  // ❌ String "85"
```
- System detects type mismatch
- Automatically retries with clarified prompt
- Instructs LLM: "score must be an integer (whole number), not a string"
- LLM returns: `{"score": 85}`  ✅ Integer 85

**Scenario 2: LLM returns int instead of bool**
```json
{"is_trending": 1}  // ❌ Integer 1
```
- System detects type mismatch
- Retries with: "is_trending must be a boolean (true or false)"
- LLM returns: `{"is_trending": true}`  ✅ Boolean

**Scenario 3: LLM returns float instead of int**
```json
{"score": 85.5}  // ❌ Float
```
- System rejects (score defined as int, not float)
- Retries with clarification
- LLM returns: `{"score": 86}`  ✅ Integer (rounded)

### Configuration for Type Consistency

```yaml
config:
  llm:
    temperature: 0.3  # Lower = more consistent typing
    max_retries: 3    # Allow retries for type corrections
```

**Lower temperature** (0.0-0.5) helps with:
- More consistent data types
- Fewer retry attempts needed
- More predictable outputs

**Higher temperature** (0.7-1.0):
- More creative/varied outputs
- May need more retries for types
- Better for text generation

## Type Validation Rules

### Integers (`int`)
- ✅ Whole numbers: `42`, `-10`, `0`
- ❌ Decimals: `42.5` (use `float`)
- ❌ Strings: `"42"` (will be corrected)

### Booleans (`bool`)
- ✅ True/false: `true`, `false`
- ❌ Numbers: `1`, `0`
- ❌ Strings: `"true"`, `"false"`

### Floats (`float`)
- ✅ Decimals: `0.87`, `3.14`
- ✅ Integers work: `5` → `5.0`
- ❌ Strings: `"0.87"`

### Lists (`list[str]`)
- ✅ List of strings: `["a", "b", "c"]`
- ❌ Single string: `"a,b,c"`
- ❌ Mixed types: `["a", 1, true]`
- ❌ Empty when required: `[]`

### Dicts (`dict[str, int]`)
- ✅ String keys, int values: `{"a": 1, "b": 2}`
- ❌ Wrong value type: `{"a": "1"}`
- ❌ Wrong key type: `{1: "a"}`

### Objects (`object`)
- ✅ All fields present with correct types
- ❌ Missing required fields
- ❌ Extra fields (ignored, not error)
- ❌ Wrong nested types

## What You'll Learn

- Complete type system coverage
- How automatic retry/correction works
- Multiple outputs from single node
- Type validation at multiple levels
- When to use each type
- Temperature impact on type consistency
- Debugging type mismatch errors

## Common Type Errors

### Error: "Input should be a valid integer"
```
ValidationError: score
  Input should be a valid integer [type=int_type]
```
**Cause**: LLM returned wrong type (string/float instead of int)
**Solution**: System auto-retries (up to max_retries). Usually fixes itself.

### Error: "Field required"
```
ValidationError: keywords
  Field required [type=missing]
```
**Cause**: LLM didn't include all fields in response
**Solution**:
- Check prompt clearly requests all fields
- Increase max_retries
- Simplify schema (fewer fields)

### Error: "str type expected"
```
ValidationError: keywords[0]
  Input should be a valid string [type=string_type]
```
**Cause**: List contains non-string items
**Solution**: System auto-retries with clarification

## Best Practices

1. **Be explicit in prompts about types**
   - "Return an integer from 1-100" (not "return a score")
   - "Return true or false" (not "return yes/no")

2. **Use lower temperature for type consistency**
   - `temperature: 0.0-0.3` for maximum type accuracy
   - `temperature: 0.7+` for creative text (fewer numeric types)

3. **Match types to use case**
   - Counts, IDs → `int`
   - Flags, toggles → `bool`
   - Percentages, scores → `float` or `int` (pick one)
   - Categories → `list[str]`
   - Mappings → `dict[str, T]`

4. **Start simple, add complexity**
   - Start with basic types (str, int)
   - Add collections (lists, dicts) once working
   - Add nested objects last

5. **Test with verbose mode**
   ```bash
   configurable-agents run type_enforcement.yaml \
     --input topic="AI" \
     --verbose
   ```
   See exactly what LLM returns and how retries work

## Troubleshooting

**Too many retries / always failing**
- Simplify the schema (fewer output fields)
- Lower temperature (more consistent)
- More explicit prompt instructions
- Check if LLM model supports structured outputs well

**Types work sometimes, fail other times**
- Temperature too high (add randomness)
- Prompt ambiguity (be more specific)
- Add examples in prompt

**Nested object always fails**
- Start with flat schema, then nest
- Ensure all nested fields have clear descriptions
- Check nested types are supported

## Next Steps

Once type enforcement is clear:
1. Combine types in your own workflows
2. Add validation logic (T-018 improvements coming)
3. Experiment with complex nested structures
4. Build real applications with type-safe outputs
