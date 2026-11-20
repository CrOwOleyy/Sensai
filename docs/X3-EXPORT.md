# [X3] Export & Publication

## What It Does

Allows users and developers to export conversation history into clean, portable formats:
- **Markdown (`.md`)**: A formatted transcript with headings, user questions, assistant answers, and timestamps, ideal for study notes and archiving.
- **JSON (`.json`)**: A machine-readable structure containing session metadata and ordered message turns, ready for data pipelines or automated evals.

Internal system prompts (personas, memory instructions, raw system instructions) are excluded from exports to keep artifacts focused and clean.

## Usage

### In the CLI (Interactive)

Inside any active CLI conversation:
```text
/export markdown export/notes.md
/export json export/session.json
```

### In the CLI (One-shot)

Export the latest session directly from the command line:
```bash
python -m sensai --export markdown export/latest.md
python -m sensai --export json export/latest.json
```

### In the Web UI

Click the **Export MD** or **Export JSON** buttons in the top navigation bar to trigger a browser file download of the current session.

