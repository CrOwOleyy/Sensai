from sensai.core import db
from sensai.features.structured_memory import store
from sensai.features.structured_memory.tools import dispatch


def _connect():
    return db.connect(":memory:", schemas=(store.SCHEMA,))


def test_remember_and_recall():
    conn = _connect()

    result = dispatch(conn, "remember_fact", {"key": "allergy", "value": "penicillin"})
    assert "allergy" in result

    assert dispatch(conn, "recall_fact", {"key": "allergy"}) == "penicillin"


def test_recall_missing_fact():
    conn = _connect()
    assert "No fact stored" in dispatch(conn, "recall_fact", {"key": "unknown"})


def test_list_facts():
    conn = _connect()
    assert dispatch(conn, "list_facts", {}) == "No facts stored yet."

    dispatch(conn, "remember_fact", {"key": "language", "value": "Python"})
    result = dispatch(conn, "list_facts", {})
    assert "language" in result and "Python" in result


def test_forget_fact():
    conn = _connect()
    dispatch(conn, "remember_fact", {"key": "language", "value": "Python"})

    assert "Deleted" in dispatch(conn, "forget_fact", {"key": "language"})
    assert "No fact stored" in dispatch(conn, "forget_fact", {"key": "language"})


def test_unknown_tool():
    assert "Unknown tool" in dispatch(_connect(), "not_a_tool", {})
