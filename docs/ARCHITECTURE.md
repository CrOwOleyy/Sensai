# Sensai Architecture

## Overview

Sensai is a modular AI assistant built on a **core + features** architecture. Each feature is self-contained, owns its own SQLite tables, and plugs into the shared CLI.

```
┌─────────────────────────────────────────────┐
│         sensai/core/                        │
│  ┌─────────────────────────────────────┐   │
│  │ cli.py (chat loop, feature wiring)  │   │
│  │ config.py (Ollama config)           │   │
│  │ ollama_client.py (HTTP to Ollama)   │   │
│  │ db.py (SQLite connection helper)    │   │
│  │ prompt.py (system prompt assembly)  │   │
│  └─────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
           ↓ (wires & assembles)
┌─────────────────────────────────────────────┐
│     sensai/features/                        │
│  ┌──────────────────────────────────────┐   │
│  │ session_persistence/                 │   │
│  │  ├── store.py (sessions, messages)  │   │
│  │  └── __init__.py                    │   │
│  ├──────────────────────────────────────┤   │
│  │ structured_memory/                   │   │
│  │  ├── store.py (facts table)         │   │
│  │  ├── tools.py (remember/recall...)  │   │
│  │  ├── resolver.py (tool-call loop)   │   │
│  │  └── __init__.py                    │   │
│  └──────────────────────────────────────┘   │
└─────────────────────────────────────────────┘
```

## The Core

### `sensai/core/cli.py` — Chat Loop

The main entry point. Wires everything together:

1. Parse CLI args (`--model`, `--resume`, `--set-profile`, etc.)
2. Connect to SQLite, load schemas from all features
3. Load profile from session persistence
4. Build system prompt by gathering instructions from each feature
5. Load prior conversation (if `--resume`)
6. Enter chat loop:
   - Read user input
   - Save to session (via session_persistence)
   - Call `resolve_tool_calls()` (from structured_memory)
   - Stream response from Ollama
   - Save response to session

### `sensai/core/ollama_client.py`

Direct HTTP calls to the Ollama API. Two entry points:

- `stream_chat(...)` → yields response tokens one by one (for streaming)
- `chat(...)` → returns full response dict with tool calls (for non-streaming)

No LLM framework, no abstraction layer — just `requests.post()` to `http://ollama_url/api/chat`.

### `sensai/core/prompt.py`

Builds the system prompt by assembling:

1. **Base identity** → `"You are Sensai, a helpful personal assistant."`
2. **Feature instructions** → each feature contributes its own instructions (e.g., memory_tools.INSTRUCTIONS)
3. **User profile** → if `--set-profile name=X`, add `"Known user profile: - name: X"`

Result → injected into the first message as `{"role": "system", "content": "..."}`.

### `sensai/core/db.py`

Thin wrapper around SQLite. One function:

```python
conn = db.connect("sensai.db", schemas=(
    session_persistence.SCHEMA,
    structured_memory.SCHEMA,
))
```

Each feature passes its `SCHEMA` (CREATE TABLE statements). `db.connect()` runs them all on startup.

## Features

Each feature is a package under `sensai/features/`. It owns:

1. **`store.py`** — SQLite schema + CRUD functions
2. **`__init__.py`** — exports what the core needs to import
3. **Optionally:** `tools.py` (tool definitions), `resolver.py` (tool execution), etc.

### Adding a Feature

1. Create `sensai/features/<name>/`
2. Define `SCHEMA` (CREATE TABLE statements) in `store.py`
3. Implement CRUD functions (get, set, list, delete)
4. Wire into `cli.py` :
   ```python
   from sensai.features.<name> import store
   
   conn = db.connect(args.db, schemas=(session_store.SCHEMA, memory_store.SCHEMA, store.SCHEMA))
   # ... use store functions in your logic ...
   ```
5. Add tests under `tests/features/<name>/`

See [ADDING-FEATURES.md](ADDING-FEATURES.md) for a worked example.

## Session vs. Memory vs. Tools

- **Session** → full conversation history (every turn). Persists across CLI restarts (`--resume`).
- **Profile** → key-value user metadata. Injected into system prompt at startup.
- **Facts** (Memory) → structured facts the model stores/retrieves via tool calls. Durable across sessions.
- **Tools** → functions the model can invoke mid-generation (remember_fact, recall_fact, etc.).

## Database Schema

```sql
-- session_persistence/store.py
CREATE TABLE sessions (id INTEGER PRIMARY KEY, created_at TEXT);
CREATE TABLE messages (id, session_id, role TEXT, content TEXT, created_at TEXT);
CREATE TABLE profile (key TEXT PRIMARY KEY, value TEXT);

-- structured_memory/store.py
CREATE TABLE facts (key TEXT PRIMARY KEY, value TEXT, created_at TEXT, updated_at TEXT);
```

All in one `sensai.db` file. No migrations — schemas are created on first run.

## Testing

- Unit tests in `tests/core/` and `tests/features/<name>/` — mock dependencies, test in isolation.
- Integration tests would need Ollama running and can test end-to-end (manual so far).
- Run all: `pytest`
