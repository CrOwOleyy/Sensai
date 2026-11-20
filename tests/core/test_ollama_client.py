from unittest.mock import MagicMock, patch

from sensai.core import ollama_client


def _fake_response(payload_holder):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = {"message": {"role": "assistant", "content": "{}"}}

    def capture(url, json, stream, timeout):
        payload_holder.update(json)
        return response

    return capture, response


def test_chat_includes_format_in_payload():
    captured = {}
    capture, _ = _fake_response(captured)

    schema = {"type": "object", "properties": {"name": {"type": "string"}}}
    with patch("sensai.core.ollama_client.requests.post", side_effect=capture):
        ollama_client.chat("http://host", "m", [{"role": "user", "content": "hi"}], format_=schema)

    assert captured["format"] == schema
    assert captured["stream"] is False


def test_chat_omits_format_when_none():
    captured = {}
    capture, _ = _fake_response(captured)

    with patch("sensai.core.ollama_client.requests.post", side_effect=capture):
        ollama_client.chat("http://host", "m", [{"role": "user", "content": "hi"}])

    assert "format" not in captured


def test_chat_includes_options_in_payload():
    captured = {}
    capture, _ = _fake_response(captured)
    options = {"temperature": 0.2, "num_ctx": 8192}

    with patch("sensai.core.ollama_client.requests.post", side_effect=capture):
        ollama_client.chat("http://host", "m", [{"role": "user", "content": "hi"}], options=options)

    assert captured["options"] == options


def test_chat_omits_options_when_empty():
    captured = {}
    capture, _ = _fake_response(captured)

    with patch("sensai.core.ollama_client.requests.post", side_effect=capture):
        ollama_client.chat("http://host", "m", [{"role": "user", "content": "hi"}], options={})

    assert "options" not in captured


def test_stream_chat_includes_options_in_payload():
    captured = {}
    capture, response = _fake_response(captured)
    response.iter_lines.return_value = [b'{"message": {"content": "ok"}, "done": true}']
    options = {"temperature": 0.2, "num_ctx": 8192}

    with patch("sensai.core.ollama_client.requests.post", side_effect=capture):
        chunks = list(
            ollama_client.stream_chat(
                "http://host", "m", [{"role": "user", "content": "hi"}], options=options
            )
        )

    assert chunks == ["ok"]
    assert captured["options"] == options
