import json
from argparse import Namespace

from sensai.core import cli


def _run_cli(tmp_path, monkeypatch, config_data, schema=None, temperature=None, num_ctx=None):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        config_data if isinstance(config_data, str) else json.dumps(config_data), encoding="utf-8"
    )
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: Namespace(
            model="m",
            config=str(config_path),
            temperature=temperature,
            num_ctx=num_ctx,
            db=str(tmp_path / "sensai.db"),
            resume=False,
            set_profile=[],
            persona=None,
            schema=schema,
            export=None,
        ),
    )
    inputs = iter(["hello", "exit"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    cli.run()


def test_options_reach_tool_loop_and_stream(tmp_path, monkeypatch):
    seen = {}

    def fake_resolve(conn, url, model, messages, options=None):
        seen["resolve"] = options
        return messages

    def fake_stream(url, model, messages, usage=None, options=None):
        seen["stream"] = options
        yield "ok"

    monkeypatch.setattr(cli, "resolve_tool_calls", fake_resolve)
    monkeypatch.setattr(cli, "stream_chat", fake_stream)

    _run_cli(tmp_path, monkeypatch, {"temperature": 0.2, "num_ctx": 8192})

    expected = {"temperature": 0.2, "num_ctx": 8192}
    assert seen == {"resolve": expected, "stream": expected}


def test_cli_flags_override_config_file(tmp_path, monkeypatch):
    seen = {}

    def fake_resolve(conn, url, model, messages, options=None):
        seen["resolve"] = options
        return messages

    monkeypatch.setattr(cli, "resolve_tool_calls", fake_resolve)
    monkeypatch.setattr(cli, "stream_chat", lambda *a, **k: iter(["ok"]))

    _run_cli(tmp_path, monkeypatch, {"temperature": 0.2}, temperature=0.0, num_ctx=2048)

    assert seen["resolve"] == {"temperature": 0.0, "num_ctx": 2048}


def test_options_reach_structured_output_mode(tmp_path, monkeypatch):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(json.dumps({"type": "object"}), encoding="utf-8")
    seen = {}

    def fake_chat(url, model, messages, tools=None, format_=None, options=None):
        seen["chat"] = options
        return {"role": "assistant", "content": "{}"}

    monkeypatch.setattr(cli, "chat", fake_chat)

    _run_cli(tmp_path, monkeypatch, {"num_ctx": 8192}, schema=str(schema_path))

    assert seen["chat"] == {"num_ctx": 8192}


def test_invalid_config_is_reported_without_traceback(tmp_path, monkeypatch, capsys):
    _run_cli(tmp_path, monkeypatch, {"temperature": -1})
    assert "[error] 'temperature' must be a number >= 0" in capsys.readouterr().out


def test_malformed_config_is_reported_without_traceback(tmp_path, monkeypatch, capsys):
    _run_cli(tmp_path, monkeypatch, "{bad json")
    assert "is not valid JSON" in capsys.readouterr().out
