from sensai.core import db
from sensai.features.structured_memory import store


def _connect():
    return db.connect(":memory:", schemas=(store.SCHEMA,))


def test_facts_crud():
    conn = _connect()
    store.upsert_fact(conn, "allergy", "penicillin")

    assert store.get_fact(conn, "allergy") == "penicillin"
    assert store.list_facts(conn) == {"allergy": "penicillin"}

    store.upsert_fact(conn, "allergy", "peanuts")
    assert store.get_fact(conn, "allergy") == "peanuts"

    assert store.delete_fact(conn, "allergy") is True
    assert store.get_fact(conn, "allergy") is None
    assert store.delete_fact(conn, "allergy") is False
