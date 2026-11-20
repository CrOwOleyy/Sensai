import json

import pytest
from fastapi.testclient import TestClient

from sensai.core.config import Config
from sensai.core.ollama_client import OllamaConnectionError
from sensai.features.session_persistence import store as session_store
from sensai.features.web_ui import server


@pytest.fixture
def client(tmp_path, monkeypatch):
    personas = tmp_path / "personas"
    personas.mkdir()
    (personas / "tutor.json").write_text(json.dumps({"name": "Tutor", "role": "a math tutor"}))
    (personas / "coach.json").write_text(json.dumps({"name": "Coach", "role": "a coding coach"}))

    monkeypatch.setattr(server, "list_models", lambda url: ["llama3.2"])
    monkeypatch.setattr(server, "resolve_tool_calls", lambda conn, url, model, messages, options=None: messages)
    captured = {}

    def fake_stream(url, model, messages, usage=None, options=None):
        captured["model"] = model
        captured["messages"] = messages
        yield "Hel"
        yield "lo"
        usage.update(prompt_tokens=7, completion_tokens=2)

    monkeypatch.setattr(server, "stream_chat", fake_stream)
    app = server.create_app(
        Config(model="llama3.2", ollama_url="http://x", persona="tutor"),
        db_path=str(tmp_path / "t.db"),
        personas_dir=str(personas),
    )
    test_client = TestClient(app)
    test_client.captured = captured
    return test_client


def events(response):
    return [json.loads(line[6:]) for line in response.text.split("\n\n") if line.startswith("data: ")]


def test_state_lists_personas_models_and_profile(client):
    state = client.get("/api/state").json()
    assert state["personas"] == ["coach", "tutor"]
    assert state["models"] == ["llama3.2"]
    assert state["model"] == "llama3.2"
    assert state["persona"] == "tutor"


def test_chat_streams_tokens_usage_and_persists(client):
    sid = client.post("/api/sessions").json()["id"]
    res = client.post("/api/chat", json={"session_id": sid, "message": "hi"})
    evs = events(res)
    assert "".join(e["content"] for e in evs if e["type"] == "token") == "Hello"
    assert {"type": "usage", "prompt_tokens": 7, "completion_tokens": 2} in evs
    assert evs[-1] == {"type": "done"}

    saved = client.get(f"/api/sessions/{sid}").json()["messages"]
    assert saved == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    assert "a math tutor" in client.captured["messages"][0]["content"]


def test_persona_switch_keeps_history(client):
    sid = client.post("/api/sessions").json()["id"]
    client.post("/api/chat", json={"session_id": sid, "message": "one", "persona": "tutor"})
    client.post("/api/chat", json={"session_id": sid, "message": "two", "persona": "coach"})
    roles = [m["role"] for m in client.captured["messages"]]
    assert roles == ["system", "user", "assistant", "user"]
    assert "coding coach" in client.captured["messages"][0]["content"]


def test_model_override_per_request(client):
    sid = client.post("/api/sessions").json()["id"]
    client.post("/api/chat", json={"session_id": sid, "message": "hi", "model": "other"})
    assert client.captured["model"] == "other"


def test_empty_message_and_unknown_persona_rejected(client):
    sid = client.post("/api/sessions").json()["id"]
    assert client.post("/api/chat", json={"session_id": sid, "message": "  "}).status_code == 400
    bad = client.post("/api/chat", json={"session_id": sid, "message": "x", "persona": "nope"})
    assert bad.status_code == 400


def test_input_guardrail_blocks_pii_in_web_ui(client):
    sid = client.post("/api/sessions").json()["id"]
    bad = client.post("/api/chat", json={"session_id": sid, "message": "my email is user@example.com"})
    assert bad.status_code == 400
    assert "email" in bad.json()["detail"].lower()


def test_output_guardrail_redacts_pii_in_web_ui(client, monkeypatch):
    def pii_stream(url, model, messages, usage=None, options=None):
        captured = messages
        yield "Contact me at user@example.com"
        usage.update(prompt_tokens=3, completion_tokens=4)

    captured = {}
    monkeypatch.setattr(server, "stream_chat", pii_stream)
    monkeypatch.setattr(server, "resolve_tool_calls", lambda conn, url, model, messages, options=None: messages)

    sid = client.post("/api/sessions").json()["id"]
    res = client.post("/api/chat", json={"session_id": sid, "message": "hello"})
    evs = events(res)

    token_events = [e["content"] for e in evs if e["type"] == "token"]
    assert token_events
    assert "user@example.com" not in "".join(token_events)

    saved = client.get(f"/api/sessions/{sid}").json()["messages"]
    assert saved[-1]["content"] == "Contact me at [REDACTED EMAIL]"


def test_ollama_error_is_reported_and_nothing_saved(client, monkeypatch):
    def boom(*args, **kwargs):
        raise OllamaConnectionError("Ollama down")
        yield

    monkeypatch.setattr(server, "stream_chat", boom)
    sid = client.post("/api/sessions").json()["id"]
    evs = events(client.post("/api/chat", json={"session_id": sid, "message": "hi"}))
    assert evs == [{"type": "error", "message": "Ollama down"}]
    assert client.get(f"/api/sessions/{sid}").json()["messages"] == []


def test_profile_update_is_used_in_prompt(client):
    client.put("/api/profile", json={"values": {"name": "Leyy"}})
    sid = client.post("/api/sessions").json()["id"]
    client.post("/api/chat", json={"session_id": sid, "message": "hi"})
    assert "name: Leyy" in client.captured["messages"][0]["content"]


def test_unknown_session_404(client):
    assert client.get("/api/sessions/999").status_code == 404


def test_export_session_markdown(client):
    sid = client.post("/api/sessions").json()["id"]
    client.post("/api/chat", json={"session_id": sid, "message": "alohomora"})
    res = client.get(f"/api/sessions/{sid}/export?format=markdown")
    assert res.status_code == 200
    assert "text/markdown" in res.headers["content-type"]
    assert "# Session" in res.text
    assert "alohomora" in res.text


def test_export_session_json(client):
    sid = client.post("/api/sessions").json()["id"]
    client.post("/api/chat", json={"session_id": sid, "message": "lumos"})
    res = client.get(f"/api/sessions/{sid}/export?format=json")
    assert res.status_code == 200
    assert "application/json" in res.headers["content-type"]
    data = res.json()
    assert data["session_id"] == sid
    assert len(data["messages"]) == 2


def test_export_unknown_session_or_format(client):
    assert client.get("/api/sessions/999/export?format=markdown").status_code == 404
    sid = client.post("/api/sessions").json()["id"]
    assert client.get(f"/api/sessions/{sid}/export?format=invalid").status_code == 400


def test_generation_options_reach_every_model_call(tmp_path, monkeypatch):
    options = {"temperature": 0.2, "num_ctx": 8192}
    seen = {}

    def fake_resolve(conn, url, model, messages, options=None):
        seen["resolve"] = options
        return messages

    def fake_stream(url, model, messages, usage=None, options=None):
        seen["stream"] = options
        yield "ok"

    monkeypatch.setattr(server, "resolve_tool_calls", fake_resolve)
    monkeypatch.setattr(server, "stream_chat", fake_stream)
    app = server.create_app(
        Config(model="m", ollama_url="http://x", temperature=0.2, num_ctx=8192),
        db_path=str(tmp_path / "t.db"),
    )
    test_client = TestClient(app)
    sid = test_client.post("/api/sessions").json()["id"]
    test_client.post("/api/chat", json={"session_id": sid, "message": "hi"})

    assert seen == {"resolve": options, "stream": options}
