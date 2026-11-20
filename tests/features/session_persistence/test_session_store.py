from sensai.core import db
from sensai.features.session_persistence import store


def _connect():
    return db.connect(":memory:", schemas=(store.SCHEMA,))


def test_session_and_message_round_trip():
    conn = _connect()
    session_id = store.create_session(conn)

    store.save_message(conn, session_id, "user", "hello")
    store.save_message(conn, session_id, "assistant", "hi there")

    assert store.load_messages(conn, session_id) == [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    assert store.get_latest_session_id(conn) == session_id


def test_profile_set_and_get():
    conn = _connect()
    store.set_profile_value(conn, "name", "Ryad")
    store.set_profile_value(conn, "name", "Leyy")

    assert store.get_profile(conn) == {"name": "Leyy"}
