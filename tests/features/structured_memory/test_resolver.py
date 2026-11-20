from unittest.mock import patch

from sensai.core import db
from sensai.features.structured_memory import store
from sensai.features.structured_memory.resolver import resolve_tool_calls


def _connect():
    return db.connect(":memory:", schemas=(store.SCHEMA,))


def test_tool_call_is_executed_then_loop_stops():
    conn = _connect()
    messages = [{"role": "user", "content": "my name is Leyy"}]

    responses = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "remember_fact", "arguments": {"key": "name", "value": "Leyy"}}}
            ],
        },
        {"role": "assistant", "content": "Got it."},
    ]

    with patch("sensai.features.structured_memory.resolver.chat", side_effect=responses):
        result = resolve_tool_calls(conn, "http://localhost:11434", "test-model", messages)

    assert store.get_fact(conn, "name") == "Leyy"
    assert "tool" in [m["role"] for m in result]


def test_no_tool_calls_leaves_messages_unchanged():
    conn = _connect()
    messages = [{"role": "user", "content": "hi"}]

    with patch(
        "sensai.features.structured_memory.resolver.chat",
        return_value={"role": "assistant", "content": "hello"},
    ):
        result = resolve_tool_calls(conn, "http://localhost:11434", "test-model", messages)

    assert result == messages


def test_options_reach_every_tool_round():
    conn = _connect()
    options = {"temperature": 0.2, "num_ctx": 8192}
    responses = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"function": {"name": "remember_fact", "arguments": {"key": "name", "value": "Leyy"}}}
            ],
        },
        {"role": "assistant", "content": "Got it."},
    ]

    with patch("sensai.features.structured_memory.resolver.chat", side_effect=responses) as chat:
        resolve_tool_calls(conn, "http://x", "m", [{"role": "user", "content": "hi"}], options=options)

    assert chat.call_count == 2
    assert all(call.kwargs["options"] == options for call in chat.call_args_list)
