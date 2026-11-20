# [X1] Web UI

## What It Does

Provides a decoupled web frontend for the Sensai assistant served through a FastAPI backend.
It allows students and users to chat with the assistant directly from any web browser, while sharing the exact same SQLite database, memory tools, guardrails, and persona profiles as the CLI.

## Key Features

- **Streaming Responses**: Live Server-Sent Events (SSE) stream tokens as the model generates them.
- **Session Sidebar**: Lists prior conversations with timestamps and initial message previews. Clicking any conversation reloads its complete history.
- **Mid-Session Switcher**: Dropdowns to switch persona (e.g., from Snape to Dumbledore) or Ollama model on the fly without losing context.
- **Token Usage Observability**: Displays prompt, completion, and total tokens used on the latest turn.
- **Profile Editor**: Modal to inspect and edit user profile keys (e.g., `house`, `year`, `name`), auto-injected into the system prompt.
- **Direct Exports**: Buttons to export conversations as Markdown or JSON directly from the browser.

## Architecture

```
Browser (Vanilla JS + EventSource)
        │
        ▼ (SSE / HTTP JSON)
FastAPI Server (sensai/features/web_ui/server.py)
        ├── DB & Stores (sensai.db: sessions, messages, profile, facts)
        ├── Guardrails (inspect_user_input, stream_sanitized_output)
        └── Ollama Client (stream_chat via HTTP API)
```

## Running the Web UI

```bash
python -m sensai.features.web_ui
# Or with options:
python -m sensai.features.web_ui --port 8080 --model llama3.2 --db sensai.db
```
Navigate to `http://127.0.0.1:8000` (or configured port).

