from argparse import Namespace

from sensai.core import cli


def test_cli_blocks_sensitive_user_input(tmp_path, monkeypatch, capsys):
    inputs = iter(["my password is secret", "exit"])

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

    out = capsys.readouterr().out
    assert "[guardrail]" in out
    assert "password" in out.lower()