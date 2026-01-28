# User Profile Generator (Nested State)

**File**: `nested_state.yaml`
**Complexity**: ⭐⭐ Intermediate (nested object types)

## What It Does

Generates a comprehensive user profile with nested structure, demonstrating:
- Object types with nested schemas
- List types (arrays)
- Complex state with multiple levels
- Accessing list inputs in prompts

Perfect for understanding:
- Nested state definitions
- Complex output schemas
- How LLMs can generate structured nested data
- Type enforcement at multiple levels

## Structure

- **2 input fields**: `name` (str), `interests` (list[str])
- **1 output field**: `profile` (complex nested object)
- **1 node**: Generates comprehensive profile
- **Nested structure**: Object with strings, lists, and integers

## Usage

### CLI

```bash
# Single interest
configurable-agents run nested_state.yaml \
  --input name="Alice" \
  --input 'interests=["AI", "robotics", "philosophy"]'
```

### Python

```python
from configurable_agents.runtime import run_workflow

result = run_workflow(
    "examples/nested_state.yaml",
    {
        "name": "Alice",
        "interests": ["AI", "robotics", "philosophy"]
    }
)

profile = result["profile"]
print(f"Bio: {profile['bio']}")
print(f"Traits: {profile['personality_traits']}")
print(f"Recommended: {profile['recommended_topics']}")
print(f"Score: {profile['engagement_score']}")
```

## State Schema Explained

### Input State

```yaml
name:
  type: str
  required: true

interests:
  type: list[str]
  required: true
```

### Output State (Nested Object)

```yaml
profile:
  type: object
  schema:
    bio: str                        # Simple string
    personality_traits: list[str]   # List of strings
    recommended_topics: list[str]   # List of strings
    engagement_score: int           # Integer (1-100)
  default: null                     # Starts as null
```

## How It Works

The LLM receives the prompt with user inputs and must generate a response matching the exact nested structure:

```json
{
  "profile": {
    "bio": "Alice is a curious technologist...",
    "personality_traits": ["analytical", "creative", "forward-thinking"],
    "recommended_topics": ["machine learning", "neural networks", ...],
    "engagement_score": 85
  }
}
```

**Type enforcement ensures**:
- `bio` is a string (not null, not a number)
- `personality_traits` is a list of strings (not a string, not mixed types)
- `engagement_score` is an integer (not a float, not a string)

If the LLM returns wrong types, the system automatically retries with clarified prompts.

## Expected Output

```
Result:
  name: Alice
  interests: ["AI", "robotics", "philosophy"]
  profile:
    bio: |
      Alice is a curious technologist with a passion for artificial intelligence
      and its philosophical implications. She explores the intersection of
      technology and human values.
    personality_traits:
      - Analytical
      - Philosophically-minded
      - Tech-savvy
      - Forward-thinking
      - Intellectually curious
    recommended_topics:
      - Machine Learning Ethics
      - Cognitive Robotics
      - Philosophy of Mind
      - AI Alignment
      - Transhumanism
    engagement_score: 87
```

## What You'll Learn

- Defining nested object types with `schema` keyword
- List types: `list[str]`, `list[int]`, etc.
- Complex output schemas with multiple levels
- How type enforcement works on nested structures
- Accessing list inputs in prompts: `{state.interests}`
- Default value `null` for optional complex objects

## Nested Object Best Practices

1. **Keep nesting shallow** (1-2 levels max in v0.1)
   - Deep nesting (3+ levels) supported but harder for LLMs

2. **Clear field descriptions** help LLMs understand structure
   ```yaml
   bio:
     type: str
     description: "2-3 sentence biography"
   ```

3. **Type consistency** - use typed lists when possible
   - `list[str]` better than `list` (generic)
   - Enables better validation

4. **Optional vs Required** nested objects
   - Use `default: null` for objects that might not be needed
   - LLM can skip if not relevant

## Troubleshooting

**Error: "Field 'bio' is required"**
- LLM didn't generate all fields in nested object
- System will retry automatically (up to max_retries)
- Check that prompt clearly requests all fields

**Error: "Input should be a valid list"**
- When passing interests via CLI, use JSON format
- Correct: `--input 'interests=["AI", "robotics"]'`
- Wrong: `--input interests=AI,robotics`

**Wrong types in output**
- Lower temperature for more consistent typing: `temperature: 0.3`
- Be explicit in prompt: "return an integer from 1-100"

## Next Steps

Try modifying the nested schema:
1. Add more nested levels (metadata with timestamps, locations)
2. Add different types (float for confidence scores)
3. Combine with multi-node workflow (generate → refine)
4. Add `dict` types: `social_scores: dict[str, int]`
