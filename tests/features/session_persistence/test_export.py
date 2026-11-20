import json

from sensai.features.session_persistence.export import render_json, render_markdown


def test_render_json_excludes_system_messages():
    content = render_json(
        7,
        [
            {"role": "system", "content": "ignore me"},
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
    )

    data = json.loads(content)
    assert data == {
        "session_id": 7,
        "message_count": 2,
        "messages": [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi there"},
        ],
    }


def test_render_markdown_excludes_system_messages_and_keeps_order():
    content = render_markdown(
        7,
        [
            {"role": "system", "content": "ignore me"},
            {"role": "user", "content": "hello\nworld"},
            {"role": "assistant", "content": "hi there"},
        ],
    )

    assert "# Session 7" in content
    assert "Message count: 2" in content
    assert "ignore me" not in content
    assert "## 1. User" in content
    assert "> hello" in content
    assert "> world" in content
    assert "## 2. Assistant" in content