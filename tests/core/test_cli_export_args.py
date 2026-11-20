from argparse import Namespace

from sensai.core import cli
from sensai.core import db
from sensai.features.session_persistence import store


def test_cli_export_argument_exports_latest_session_and_exits(tmp_path, monkeypatch):
    database_path = tmp_path / "sensai.db"
    conn = db.connect(str(database_path), schemas=(store.SCHEMA,))
    session_id = store.create_session(conn)
    store.save_message(conn, session_id, "user", "hello")
    store.save_message(conn, session_id, "assistant", "hi")
    conn.close()

    output_path = tmp_path / "exports" / "session.json"
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda argv=None: Namespace(
            model=None,
            config=None,
            temperature=None,
            num_ctx=None,
            db=str(database_path),
            resume=False,
            set_profile=[],
            persona=None,
            schema=None,
            export=("json", str(output_path)),
        ),
    )

    cli.run()

    assert output_path.exists()
    assert '"session_id": 1' in output_path.read_text(encoding="utf-8")