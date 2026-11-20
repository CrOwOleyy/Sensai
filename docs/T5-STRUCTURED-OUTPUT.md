# [T5] Structured Output

## What It Does

Forces the model to respond with **valid JSON conforming to a schema** you define, instead of
free-form prose. The output is validated client-side before it's shown.

Useful whenever you want to parse the model's answer programmatically — feed a database, build a
dataset, drive a UI — without scraping natural language.

## How It Works

```
You pass --schema schemas/person.json
  ↓
CLI loads & validates the schema file at startup
  ↓
Schema description added to the system prompt
  ↓
For each message:
  chat(..., format_=schema)   ← Ollama constrains generation to the schema
  ↓
validate_output(raw, schema)  ← client-side check with jsonschema
  ↓
Pretty-printed JSON shown + saved to session
```

### Two Layers of Enforcement

1. **Server-side (Ollama)** — the `format` parameter in the `/api/chat` request. Ollama constrains
   token generation so the output matches the JSON Schema. This is native to Ollama, no framework.

2. **Client-side (jsonschema)** — we still parse and validate the result ourselves. If a model
   ignores or imperfectly follows the constraint, we catch it instead of passing bad data downstream.

Belt and suspenders: the model is *guided* to produce correct JSON, and we *verify* it.

## The Ollama `format` Parameter

```python
# sensai/core/ollama_client.py

def chat(base_url, model, messages, tools=None, format_=None):
    response = _post(..., format_=format_)
    ...

# The request payload sent to Ollama:
{
  "model": "llama3.2",
  "messages": [...],
  "stream": false,
  "format": {              # ← the JSON Schema
    "type": "object",
    "properties": {
      "name": {"type": "string"},
      "age": {"type": "integer"}
    },
    "required": ["name", "age"]
  }
}
```

When `format` is a JSON Schema object, Ollama's sampler only emits tokens that keep the output valid
against it. (`format: "json"` would allow *any* valid JSON — we use a full schema for structure.)

## Schema Handling

```python
# sensai/features/structured_output/schema.py

def load_schema(path) -> dict
    # Read the file, parse JSON, verify it's a valid JSON Schema (Draft 2020-12).
    # Raises SchemaError with a clear message on any problem.

def validate_output(output: str, schema: dict) -> dict
    # Parse the model output as JSON, validate against the schema.
    # Returns the parsed dict, or raises SchemaError.

def describe_schema(schema: dict) -> str
    # Build a short instruction for the system prompt, e.g.
    # "Respond only with JSON matching Person, containing these fields: name, age, occupation, skills."
```

## Usage

### Basic

```bash
python -m sensai --schema schemas/person.json
```

```
Sensai chatbot — model: llama3.2, mode: JSON schema (type 'exit' to quit)

You: Generate a fictional software engineer named Ada, 30 years old
Assistant (JSON):
{
  "name": "Ada",
  "age": 30,
  "occupation": "Software Engineer",
  "skills": ["Python", "Distributed Systems", "Algorithms"]
}
```

### Example Schema

```json
// schemas/person.json
{
  "title": "Person",
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "age": { "type": "integer" },
    "occupation": { "type": "string" },
    "skills": { "type": "array", "items": { "type": "string" } }
  },
  "required": ["name", "age", "occupation", "skills"],
  "additionalProperties": false
}
```

`additionalProperties: false` means the model cannot invent extra fields — the output is exactly the
shape you asked for.

### Write Your Own Schema

Any valid [JSON Schema](https://json-schema.org/) works. Drop a `.json` file in `schemas/` and point
`--schema` at it:

```json
{
  "title": "TodoItem",
  "type": "object",
  "properties": {
    "task": { "type": "string" },
    "priority": { "type": "string", "enum": ["low", "medium", "high"] },
    "done": { "type": "boolean" }
  },
  "required": ["task", "priority", "done"],
  "additionalProperties": false
}
```

## Error Handling

| Situation | What happens |
|-----------|--------------|
| Schema file missing | `[error] Could not read schema file '...'` at startup, exits before the chat loop |
| Schema file not JSON | `[error] Schema file '...' is not valid JSON` at startup |
| File isn't a valid JSON Schema | `[error] Schema file '...' is not a valid JSON Schema` at startup |
| Model output isn't valid JSON | `[schema error] Model output is not valid JSON` + raw output, turn discarded |
| Output doesn't match schema | `[schema error] Output does not match schema: ...` + raw output, turn discarded |

When a turn is discarded, the user message is rolled back from history so the session stays clean.

## Interaction With Other Features

In `--schema` mode the CLI **bypasses the memory tools** ([M3]) and streaming. This is intentional:
a strict JSON response and mid-stream tool calls don't mix. You get one clean, validated JSON object
per turn.

Structured responses **are** still saved to the session ([M1]), so `--resume` works normally and the
JSON turns reappear in history.

## Implementation Files

```
sensai/features/structured_output/
  schema.py        load_schema, validate_output, describe_schema, SchemaError
  __init__.py

sensai/core/
  ollama_client.py  chat() now accepts format_ (passed as Ollama's "format")
  cli.py            --schema flag, structured-output branch in the loop

schemas/
  person.json      example schema for the demo

tests/features/structured_output/
  test_schema.py   load/validate/describe coverage
tests/core/
  test_ollama_client.py  verifies format_ reaches the request payload
```

## Why This Matters (for the keynote)

- **Real-world parallel:** OpenAI's Structured Outputs API, any pipeline that parses LLM responses.
- **The tradeoff we made:** server-side constraint *and* client-side validation. We could have
  trusted Ollama's `format` alone, but validating ourselves means a bad response never silently
  reaches a downstream consumer.
- **Limitation:** streaming is disabled in this mode (we need the full document to validate it).

## Dependencies

- [`jsonschema`](https://pypi.org/project/jsonschema/) — schema validation (a utility package, not an
  LLM framework). Added to `requirements.txt`.
