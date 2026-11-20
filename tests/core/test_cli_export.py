from argparse import Namespace

from sensai.core import cli


def test_cli_export_command_writes_markdown(tmp_path, monkeypatch, capsys):
    output_path = tmp_path / "exports" / "session.md"
    inputs = iter(["/export markdown " + str(output_path), "exit"])

    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: Namespace(
            model=None,
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

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "# Session" in content
    assert "Message count: 0" in content
    assert "Exported session" in capsys.readouterr().out