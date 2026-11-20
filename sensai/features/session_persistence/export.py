from __future__ import annotations

import json


def _exportable_messages(messages: list[dict]) -> list[dict]:
    return [message for message in messages if message.get("role") != "system"]


def render_json(session_id: int, messages: list[dict]) -> str:
    exported_messages = _exportable_messages(messages)
    payload = {
        "session_id": session_id,
        "message_count": len(exported_messages),
        "messages": exported_messages,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


def _format_markdown_message(content: str) -> list[str]:
    lines = content.splitlines() or [""]
    return [f"> {line}" if line else ">" for line in lines]


def render_markdown(session_id: int, messages: list[dict]) -> str:
    exported_messages = _exportable_messages(messages)
    lines = [
        f"# Session {session_id}",
        "",
        f"Message count: {len(exported_messages)}",
        "",
    ]
    for index, message in enumerate(exported_messages, start=1):
        role = message.get("role", "unknown").capitalize()
        content = message.get("content", "")
        lines.append(f"## {index}. {role}")
        lines.extend(_format_markdown_message(content))
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"