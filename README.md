# Sensai — Hogwarts Edition ⚡

A local AI tutor and chatbot for Hogwarts students, backed by [Ollama](https://ollama.com) and built without any LLM framework (no LangChain, LlamaIndex, Haystack, etc.) — all model calls go through the Ollama HTTP API directly.

Consult legendary Hogwarts figures (Professor Snape, Professor McGonagall, Professor Dumbledore, Hagrid, and The Sorting Hat), preserve study sessions, remember student traits and house points, export revision notes, and stay protected with built-in guardrails.

## Setup

1. Install [Ollama](https://ollama.com/download) and pull a model:
   ```bash
   ollama pull llama3.2
   ```
2. Install Python dependencies (Python 3.10+):
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### CLI Interface

```bash
python -m sensai
```

Options:
- `--model <name>` — override the model for this run (takes priority over `config.json`)
- `--temperature <value>`, override the sampling temperature for this run
- `--num-ctx <tokens>`, override the context window size for this run
- `--config <path>` — use a different config file (defaults to `config.json`)
- `--db <path>` — SQLite database path (defaults to `sensai.db`)
- `--resume` — continue the most recent session instead of starting a new one
- `--set-profile KEY=VALUE` — set a persistent profile entry (repeatable, e.g. `--set-profile house=Gryffindor year=3`)
- `--persona <name>` — start with a persona from `personas/` (`dumbledore`, `snape`, `mcgonagall`, `hagrid`, `sorting_hat`)
- `--schema <path>` — constrain responses to valid JSON matching a JSON Schema file

Examples:
```bash
# Start a tutoring session with Professor Snape
python -m sensai --persona snape

# Configure student profile and resume past session
python -m sensai --set-profile name=Harry --set-profile house=Gryffindor --resume
```

Interactive CLI commands:
- `/help` — list interactive commands
- `/personas` — display all available Hogwarts personas
- `/persona <name>` — switch professor mid-conversation while retaining context (e.g. `/persona mcgonagall`)
- `/export <json|markdown> <path>` — export current conversation transcript
- `exit` or `quit` — end the session

Structured output examples:
```bash
# Generate a validated potion recipe with Professor Snape
python -m sensai --persona snape --schema schemas/potion.json

# Generate a spell record with Professor McGonagall
python -m sensai --persona mcgonagall --schema schemas/spell.json
```

Exporting sessions directly from the terminal:
```bash
python -m sensai --export json export/session.json
python -m sensai --export markdown export/session.md
```

### Web Interface

```bash
python -m sensai.features.web_ui            # http://127.0.0.1:8000
python -m sensai.features.web_ui --port 8080 --model llama3.2 --db sensai.db
```

The web interface shares the same SQLite database and features as the CLI:
- Progressive response streaming
- Session sidebar with full history
- Live persona (professor) and model switching mid-conversation
- Token usage counters (prompt, completion, total)
- Student profile editor (auto-injected into system prompt)
- One-click conversation exports to Markdown and JSON

### Configuration

`config.json` at the repo root:
```json
{
  "model": "llama3.2",
  "ollama_url": "http://127.0.0.1:11434",
  "persona": "dumbledore",
  "temperature": 0.8,
  "num_ctx": 4096
}
```

| Setting | Effect | Notes |
|---------|--------|-------|
| `temperature` | Randomness of the answers (number >= 0) | `0` gives near-identical answers for the same prompt; higher values vary more |
| `num_ctx` | Context window, in tokens (integer >= 1) | Above the limit, Ollama silently truncates the prompt. A larger value uses more memory, and changing it makes Ollama reload the model |

Both are optional: if a setting is removed, Ollama's default applies. They apply to the CLI and the web interface, to every model call of a turn. The `--temperature` and `--num-ctx` flags take priority over the file, and both commands accept them:

```bash
python -m sensai --temperature 0 --num-ctx 8192
python -m sensai.features.web_ui --temperature 0.3 --num-ctx 2048
```

An invalid value is reported at startup, before any model call. Run `ollama ps` to see the context size actually loaded.

## Features Implemented

- **[B1] Functional CLI chatbot**: streaming responses, in-session history, clean error handling, configurable model.
- **[M1] Session persistence & profiles**: `--resume` continues previous sessions, `--set-profile` persists student metadata across restarts.
- **[M3] External structured memory**: LLM tool calls (`remember_fact`, `recall_fact`, `forget_fact`, `list_facts`) backed by SQLite.
- **[T5] Structured output**: `--schema` forces JSON Schema adherence, validated client-side before rendering.
- **[A5] Personas**: Hogwarts professors with distinctive pedagogical styles and tones, switchable at runtime without losing conversation history.
- **[X1] Web UI**: responsive browser interface with streaming, live switcher, token metrics, and profile modal.
- **[X3] Export & Publication**: export transcripts to Markdown and JSON via CLI commands, CLI flags, and Web UI download buttons.
- **[EV2] Content & Privacy Guardrails**: input interceptor blocking secrets, banking, and PII; output interceptor redacting leaked credentials or identifiers.

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest
```


---
_Note: the subject PDF, course archives and audio files were left out of this public copy._
