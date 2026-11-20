from argparse import Namespace
import json

from sensai.core import cli


def test_cli_starts_with_configured_persona(tmp_path, monkeypatch, capsys):
    personas_dir = tmp_path / "personas"
    personas_dir.mkdir()
    (personas_dir / "snape.json").write_text(
        json.dumps({
            "name": "Professor Snape",
            "role": "Potions Master",
            "tone": "curt",
            "scope": "Potions only",
        }),
        encoding="utf-8",
    )

    inputs = iter(["exit"])

    monkeypatch.setattr(
        cli,
        "load_persona",
        lambda name: json.loads((personas_dir / f"{name}.json").read_text(encoding="utf-8")),
    )
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: Namespace(
            model="llama3.2",
            config=None,
            temperature=None,
            num_ctx=None,
            db=str(tmp_path / "sensai.db"),
            resume=False,
            set_profile=[],
            persona="snape",
            schema=None,
            export=None,
        ),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    cli.run()

    out = capsys.readouterr().out
    assert "persona: Professor Snape" in out


def test_cli_switch_persona_and_help(tmp_path, monkeypatch, capsys):
    personas = {
        "dumbledore": {
            "name": "Professor Dumbledore",
            "role": "Headmaster",
            "tone": "calm",
            "scope": "Wisdom",
        },
        "mcgonagall": {
            "name": "Professor McGonagall",
            "role": "Transfiguration teacher",
            "tone": "strict",
            "scope": "Step by step",
        },
    }

    inputs = iter(["/help", "/persona mcgonagall", "exit"])

    monkeypatch.setattr(cli, "load_persona", lambda name: personas[name])
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: Namespace(
            model="llama3.2",
            config=None,
            temperature=None,
            num_ctx=None,
            db=str(tmp_path / "sensai.db"),
            resume=False,
            set_profile=[],
            persona=None,
            schema=None,
            export=None,
        ),
    )
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))

    cli.run()

    out = capsys.readouterr().out
    assert "Available commands" in out
    assert "Switched to persona: Professor McGonagall" in out
