from __future__ import annotations

import sqlite3
from pathlib import Path


class SQLiteManager:
    def __init__(self, db_path: Path, schema_path: Path) -> None:
        self.db_path = db_path
        self.schema_path = schema_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False, timeout=30.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA busy_timeout = 30000")
        return conn

    def init_schema(self) -> None:
        sql = self.schema_path.read_text(encoding="utf-8")
        with self.connect() as conn:
            conn.executescript(sql)
            conn.commit()
