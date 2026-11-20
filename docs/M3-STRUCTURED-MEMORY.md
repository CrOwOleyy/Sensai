# [M3] External Structured Memory

## What It Does

Lets the model **actively manage** facts about you by calling tools. It stores durable key-value facts in SQLite and can remember/recall them across sessions.

### Key Idea

The model decides when to **remember** something (e.g., "the user is allergic to penicillin") and stores it. Later, it can **recall** these facts without asking you to repeat yourself.

## How It Works

### The Flow

```
User: "I'm allergic to penicillin"
  ↓
Ollama generates response + sees opportunity to remember
  ↓
Ollama calls tool: remember_fact(key="allergy", value="penicillin")
  ↓
Tool handler in sensai executes: INSERT INTO facts (key, value) ...
  ↓
Ollama continues generating its response: "Got it, I'll remember that."

Later:
User: "What allergies do I have?"
  ↓
Ollama calls: recall_fact(key="allergy")
  ↓
Returns: "penicillin"
  ↓
Ollama includes in response: "You're allergic to penicillin."
```

### The Four Tools

```python
# In sensai/features/structured_memory/tools.py

TOOL_SCHEMAS = [
    {
        "name": "remember_fact",
        "description": "Store or update a durable fact about the user",
        "parameters": {
            "key": str,     # "allergy", "language", "favorite_food"
            "value": str    # "penicillin", "Python", "sushi"
        }
    },
    {
        "name": "recall_fact",
        "description": "Retrieve a previously stored fact",
        "parameters": {"key": str}
    },
    {
        "name": "list_facts",
        "description": "List every fact currently stored",
        "parameters": {}
    },
    {
        "name": "forget_fact",
        "description": "Delete a previously stored fact",
        "parameters": {"key": str}
    }
]
```

### Tool Execution Loop

```python
# In sensai/features/structured_memory/resolver.py

def resolve_tool_calls(conn, base_url, model, messages):
    for _ in range(MAX_TOOL_ROUNDS):  # up to 4 rounds
        message = chat(base_url, model, messages, tools=TOOL_SCHEMAS)
        
        if not message.get("tool_calls"):
            return messages  # model stopped calling tools, done
        
        # Execute each tool call
        messages.append(message)
        for call in message["tool_calls"]:
            result = dispatch(conn, call["function"]["name"], call["function"]["arguments"])
            messages.append({"role": "tool", "content": result})
    
    return messages
```

**What happens:**

1. Send conversation to Ollama with `tools=TOOL_SCHEMAS`
2. Ollama returns either:
   - `{"role": "assistant", "content": "response..."}` → no tools, done
   - `{"role": "assistant", "tool_calls": [{"function": {"name": "remember_fact", ...}}]}` → has tools
3. For each tool call:
   - Execute it (write to DB, read from DB, etc.)
   - Append `{"role": "tool", "content": "result..."}` to messages
4. Send updated messages back to Ollama to continue
5. Repeat up to 4 times (to allow multi-step workflows)

### Database

```sql
-- sensai/features/structured_memory/store.py

CREATE TABLE facts (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

**Example state:**

```
facts table:
  key="allergy", value="penicillin", created_at=..., updated_at=...
  key="language", value="Python", created_at=..., updated_at=...
  key="favorite_food", value="sushi", created_at=..., updated_at=...
```

## Real Example

**Session 1:**

```
You: I'm allergic to penicillin and I code in Python
Assistant: I've got it. I'll remember that you're allergic to penicillin
           and that Python is your programming language.

[Behind the scenes:
  - Ollama called remember_fact(key="allergy", value="penicillin")
  - Ollama called remember_fact(key="language", value="Python")
  - Both were stored in the facts table]
```

**Session 2 (next day):**

```
You: Can you recommend a food for lunch?
Assistant: Given your preference for sushi... 
[Error: model didn't have this info]

But with M3:
You: What foods do I like?
Assistant: From what I remember, you haven't told me about specific food preferences.
           But I do know you're allergic to penicillin and code in Python.

[Behind the scenes:
  - Ollama called list_facts() 
  - Got back: {"allergy": "penicillin", "language": "Python"}
  - Included in response]
```

## Implementation Details

### Store Functions

All in `sensai/features/structured_memory/store.py`:

```python
def upsert_fact(conn, key: str, value: str)
    # INSERT OR UPDATE facts (key, value, created_at, updated_at)

def get_fact(conn, key: str) -> str | None
    # SELECT value FROM facts WHERE key
    # Return value or None if not found

def list_facts(conn) -> dict[str, str]
    # SELECT key, value FROM facts ORDER BY key
    # Return: {"allergy": "penicillin", "language": "Python", ...}

def delete_fact(conn, key: str) -> bool
    # DELETE FROM facts WHERE key
    # Return True if deleted, False if not found
```

### Tool Dispatch

```python
# In sensai/features/structured_memory/tools.py

def dispatch(conn, name: str, arguments: dict) -> str:
    if name == "remember_fact":
        upsert_fact(conn, arguments["key"], arguments["value"])
        return f"Stored fact '{arguments['key']}'."
    
    elif name == "recall_fact":
        value = get_fact(conn, arguments["key"])
        return value or f"No fact stored for '{arguments['key']}'."
    
    elif name == "list_facts":
        facts = list_facts(conn)
        return json.dumps(facts) if facts else "No facts stored yet."
    
    elif name == "forget_fact":
        deleted = delete_fact(conn, arguments["key"])
        return f"Deleted..." if deleted else f"No fact found..."
```

When Ollama calls a tool, this function executes it and returns the result, which gets sent back to Ollama.

### System Prompt Instructions

```python
# In sensai/features/structured_memory/tools.py

INSTRUCTIONS = (
    "You have tools to remember durable facts about the user across sessions "
    "(remember_fact, recall_fact, list_facts, forget_fact). Use remember_fact "
    "when the user shares a lasting preference or fact about themselves. "
    "Use recall_fact or list_facts when you need context you don't already have "
    "in this conversation, instead of asking the user to repeat themselves."
)
```

This is added to the system prompt so Ollama knows how to use the tools.

## Differences from Session History

| Aspect | Session (M1) | Facts (M3) |
|--------|-------------|-----------|
| **What's stored** | Every message (user + assistant) | Only facts the model decides to remember |
| **How it grows** | Linearly (every turn adds rows) | Sparsely (only on important info) |
| **Access** | Always available as context | Model calls tools to access |
| **Persistence** | Automatic (every message auto-saved) | Model-driven (model decides to remember) |
| **Example** | "I said X" → stored | "User is allergic to Y" → stored |

**Best combined:** Session = raw context for conversation flow. Facts = lasting knowledge.

## Tool-Calling Mechanics

Ollama's native `tool_calls` feature:

```
REQUEST to Ollama:
{
  "model": "llama3.2",
  "messages": [...],
  "tools": [{
    "type": "function",
    "function": {
      "name": "remember_fact",
      "description": "...",
      "parameters": {...}
    }
  }, ...]
}

RESPONSE from Ollama:
{
  "message": {
    "role": "assistant",
    "content": "",           // empty until tools are done
    "tool_calls": [{
      "function": {
        "name": "remember_fact",
        "arguments": {
          "key": "allergy",
          "value": "penicillin"
        }
      }
    }]
  }
}
```

This is natively supported by Ollama (no framework needed) — we just parse the response and execute.

## Limitations

- **Tool calls are sequential** — the model calls one tool, waits for result, then calls the next. Not parallel.
- **Model decides autonomously** — you can't force it to remember something specific. It's based on the system prompt and its training.
- **No versioning** — if you update a fact (remember_fact with the same key), the old value is lost.
- **No relationships** — facts are flat key-value, not connected to each other.

## Advanced: Multiple Tool Rounds

The resolver loops up to 4 times. This allows:

```
Round 1:
  Ollama: calls remember_fact("language", "Python")
  Tool: stores it
  Ollama: "Got it!"

Round 2:
  Ollama: sees user is also a designer, calls remember_fact("skill", "design")
  Tool: stores it
  Ollama: "I'll remember that too."

(Loop ends when Ollama stops calling tools)
```

This lets the model think through multiple facts and remember them in one turn.
