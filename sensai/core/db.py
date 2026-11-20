import sqlite3

DEFAULT_DB_PATH = "sensai.db"


def connect(db_path: str = DEFAULT_DB_PATH, schemas: tuple[str, ...] = ()) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    for schema in schemas:
        conn.executescript(schema)
    return conn
