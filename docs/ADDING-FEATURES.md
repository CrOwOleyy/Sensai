# Adding a New Feature

This guide shows you how to add a feature to Sensai following the existing pattern.

## The Pattern

Every feature is a package under `sensai/features/<name>/` with:

1. **`store.py`** — SQLite schema + CRUD functions
2. **`__init__.py`** — empty (for now)
3. **Optional:** `tools.py`, `resolver.py`, etc. for advanced features

## Example: Add a "Favorites" Feature

Let's build a simple feature that lets the model remember your favorite things (food, color, movie, etc.).

### Step 1: Create the Package

```bash
mkdir -p sensai/features/favorites
touch sensai/features/favorites/__init__.py
touch sensai/features/favorites/store.py
```

### Step 2: Define the Schema and CRUD

File: `sensai/features/favorites/store.py`

```python
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS favorites (
    category TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""

def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def set_favorite(conn: sqlite3.Connection, category: str, value: str) -> None:
    """Store or update a favorite (food, color, movie, etc.)"""
    now = _now()
    conn.execute(
        "INSERT INTO favorites (category, value, created_at, updated_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(category) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
        (category, value, now, now),
    )
    conn.commit()

def get_favorite(conn: sqlite3.Connection, category: str) -> str | None:
    """Retrieve a favorite by category"""
    row = conn.execute("SELECT value FROM favorites WHERE category = ?", (category,)).fetchone()
    return row[0] if row else None

def list_favorites(conn: sqlite3.Connection) -> dict[str, str]:
    """List all favorites"""
    rows = conn.execute("SELECT category, value FROM favorites ORDER BY category").fetchall()
    return {row[0]: row[1] for row in rows}

def delete_favorite(conn: sqlite3.Connection, category: str) -> bool:
    """Delete a favorite"""
    cur = conn.execute("DELETE FROM favorites WHERE category = ?", (category,))
    conn.commit()
    return cur.rowcount > 0
```

### Step 3: Wire Into the CLI

File: `sensai/core/cli.py`

Add the import at the top:

```python
from sensai.features.favorites import store as favorites_store
```

Update the `db.connect()` call:

```python
conn = db.connect(
    args.db,
    schemas=(
        session_store.SCHEMA,
        memory_store.SCHEMA,
        favorites_store.SCHEMA,  # ADD THIS
    ),
)
```

That's it! The feature is now wired in.

### Step 4: Add Tests

File: `tests/features/favorites/test_favorites_store.py`

```python
from sensai.core import db
from sensai.features.favorites import store

def _connect():
    return db.connect(":memory:", schemas=(store.SCHEMA,))

def test_set_and_get_favorite():
    conn = _connect()
    store.set_favorite(conn, "food", "sushi")
    
    assert store.get_favorite(conn, "food") == "sushi"
    assert store.get_favorite(conn, "color") is None

def test_list_favorites():
    conn = _connect()
    store.set_favorite(conn, "food", "sushi")
    store.set_favorite(conn, "color", "blue")
    
    assert store.list_favorites(conn) == {"food": "sushi", "color": "blue"}

def test_update_favorite():
    conn = _connect()
    store.set_favorite(conn, "food", "sushi")
    store.set_favorite(conn, "food", "pizza")
    
    assert store.get_favorite(conn, "food") == "pizza"

def test_delete_favorite():
    conn = _connect()
    store.set_favorite(conn, "food", "sushi")
    
    assert store.delete_favorite(conn, "food") is True
    assert store.get_favorite(conn, "food") is None
    assert store.delete_favorite(conn, "food") is False
```

Run the tests:

```bash
pytest tests/features/favorites/
```

### Step 5 (Optional): Add Tools

If you want the model to manage favorites via tool calls (like M3 does), create `tools.py`:

File: `sensai/features/favorites/tools.py`

```python
import json
import sqlite3
from sensai.features.favorites import store

INSTRUCTIONS = (
    "You can remember favorite things about the user (food, color, movie, etc.) "
    "using the set_favorite and recall_favorite tools."
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "set_favorite",
            "description": "Remember a user's favorite thing",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "e.g., 'food', 'color', 'movie'"},
                    "value": {"type": "string", "description": "e.g., 'sushi', 'blue', 'Inception'"},
                },
                "required": ["category", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_favorite",
            "description": "Retrieve a user's favorite",
            "parameters": {
                "type": "object",
                "properties": {"category": {"type": "string"}},
                "required": ["category"],
            },
        },
    },
]

def dispatch(conn: sqlite3.Connection, name: str, arguments: dict) -> str:
    if name == "set_favorite":
        store.set_favorite(conn, arguments["category"], arguments["value"])
        return f"Remembered: {arguments['category']} = {arguments['value']}"
    
    if name == "recall_favorite":
        value = store.get_favorite(conn, arguments["category"])
        return value or f"No favorite stored for {arguments['category']}"
    
    return f"Unknown tool: {name}"
```

Then wire into `cli.py`:

```python
from sensai.features.favorites.tools import INSTRUCTIONS as FAVORITES_INSTRUCTIONS, TOOL_SCHEMAS as FAVORITES_TOOLS

# When building system prompt:
system_prompt = build_system_prompt(
    session_store.get_profile(conn),
    [
        MEMORY_INSTRUCTIONS,
        FAVORITES_INSTRUCTIONS,  # ADD THIS
    ]
)

# When resolving tool calls:
# (This is optional for basic features. If you add tools, implement a resolver like structured_memory does.)
```

## Testing the Feature

```bash
pytest

python -m sensai
# Tell the model: "My favorite food is sushi"
# Ask: "What's my favorite food?"
# It should remember without you repeating it
```

## Best Practices

1. **Keep store.py simple** — just CRUD functions and the schema.
2. **Use transactions** — call `conn.commit()` after writes.
3. **Test in isolation** — use `:memory:` databases in tests, not real files.
4. **One table per feature** — don't share tables between features.
5. **Namespace keys** — if you have multiple related facts, prefix them: `user_food`, `user_color`, etc.
6. **Add instructions** — if your feature needs system prompt guidance, include it.

## Checklist

- [ ] Created `sensai/features/<name>/` package
- [ ] Implemented `store.py` with `SCHEMA` and CRUD functions
- [ ] Added feature to `db.connect()` schemas in `cli.py`
- [ ] Created tests in `tests/features/<name>/`
- [ ] Tests pass: `pytest`
- [ ] CLI works: `python -m sensai`
- [ ] (Optional) Added `tools.py` if model needs to manage the feature
- [ ] (Optional) Wired tools into CLI and resolver loop
