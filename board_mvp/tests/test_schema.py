import os
import sqlite3
import board_mvp.models as models


def test_schema_creation(tmp_path):
    db_path = tmp_path / "test.db"
    conn = models.init_db(str(db_path))
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = {row[0] for row in cur.fetchall()}
    expected = {"users", "quests", "verifications", "experience_ledger"}
    assert expected.issubset(tables)
    conn.close()
