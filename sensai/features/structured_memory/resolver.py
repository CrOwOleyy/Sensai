import json
import sqlite3

from sensai.core.ollama_client import chat
from sensai.features.structured_memory.tools import TOOL_SCHEMAS, dispatch

MAX_TOOL_ROUNDS = 4


def resolve_tool_calls(
    conn: sqlite3.Connection,
    base_url: str,
    model: str,
    messages: list[dict],
    options: dict | None = None,
) -> list[dict]:
    for _ in range(MAX_TOOL_ROUNDS):
        message = chat(base_url, model, messages, tools=TOOL_SCHEMAS, options=options)
        tool_calls = message.get("tool_calls")
        if not tool_calls:
            return messages

        messages.append(message)
        for call in tool_calls:
            function = call["function"]
            arguments = function["arguments"]
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            result = dispatch(conn, function["name"], arguments)
            messages.append({"role": "tool", "content": result})

    return messages
