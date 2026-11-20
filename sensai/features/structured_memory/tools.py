import json
import sqlite3

from sensai.features.structured_memory import store

INSTRUCTIONS = (
    "You have tools to remember durable facts about the user across sessions (remember_fact, "
    "recall_fact, list_facts, forget_fact). Use remember_fact when the user shares a lasting "
    "preference or fact about themselves. Use recall_fact or list_facts when you need context "
    "you don't already have in this conversation, instead of asking the user to repeat themselves."
)

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "remember_fact",
            "description": "Store or update a durable fact about the user (preference, allergy, ongoing project, etc.) for future sessions.",
            "parameters": {
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Short identifier, e.g. 'allergy' or 'preferred_language'"},
                    "value": {"type": "string", "description": "The fact to remember"},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "recall_fact",
            "description": "Retrieve a previously stored fact about the user by key.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_facts",
            "description": "List every fact currently stored about the user.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_fact",
            "description": "Delete a previously stored fact about the user by key.",
            "parameters": {
                "type": "object",
                "properties": {"key": {"type": "string"}},
                "required": ["key"],
            },
        },
    },
]


def dispatch(conn: sqlite3.Connection, name: str, arguments: dict) -> str:
    if name == "remember_fact":
        store.upsert_fact(conn, arguments["key"], arguments["value"])
        return f"Stored fact '{arguments['key']}'."

    if name == "recall_fact":
        value = store.get_fact(conn, arguments["key"])
        return value if value is not None else f"No fact stored for '{arguments['key']}'."

    if name == "list_facts":
        facts = store.list_facts(conn)
        return json.dumps(facts) if facts else "No facts stored yet."

    if name == "forget_fact":
        deleted = store.delete_fact(conn, arguments["key"])
        return f"Deleted fact '{arguments['key']}'." if deleted else f"No fact stored for '{arguments['key']}'."

    return f"Unknown tool '{name}'."
