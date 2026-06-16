import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent.parent / "sentinelai.db"


class Database:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_schema()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS models (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    model_id      TEXT NOT NULL,
                    model_name    TEXT NOT NULL,
                    version       INTEGER NOT NULL,
                    file_path     TEXT NOT NULL,
                    model_hash    TEXT NOT NULL,
                    file_size     INTEGER NOT NULL,
                    tx_hash       TEXT,
                    registered_at TEXT NOT NULL,
                    UNIQUE(model_id, version)
                );

                CREATE TABLE IF NOT EXISTS audit_log (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type    TEXT NOT NULL,
                    model_id      TEXT NOT NULL,
                    version       INTEGER,
                    model_hash    TEXT,
                    result        TEXT NOT NULL,
                    blockchain_tx TEXT,
                    notes         TEXT,
                    occurred_at   TEXT NOT NULL
                );
            """)

    def register_model(
        self,
        model_id: str,
        model_name: str,
        version: int,
        file_path: str,
        model_hash: str,
        file_size: int,
        tx_hash: Optional[str] = None
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO models
                   (model_id, model_name, version, file_path, model_hash,
                    file_size, tx_hash, registered_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (model_id, model_name, version, file_path,
                 model_hash, file_size, tx_hash, now)
            )

    def get_model(self, model_id: str, version: Optional[int] = None) -> Optional[Dict]:
        with self._conn() as conn:
            if version is not None:
                row = conn.execute(
                    "SELECT * FROM models WHERE model_id=? AND version=?",
                    (model_id, version)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM models WHERE model_id=? ORDER BY version DESC LIMIT 1",
                    (model_id,)
                ).fetchone()
        return dict(row) if row else None

    def get_model_versions(self, model_id: str) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM models WHERE model_id=? ORDER BY version ASC",
                (model_id,)
            ).fetchall()
        return [dict(r) for r in rows]

    def list_models(self) -> List[Dict]:
        with self._conn() as conn:
            rows = conn.execute("""
                SELECT m.*
                FROM models m
                INNER JOIN (
                    SELECT model_id, MAX(version) AS max_v
                    FROM models GROUP BY model_id
                ) latest ON m.model_id = latest.model_id AND m.version = latest.max_v
                ORDER BY m.registered_at DESC
            """).fetchall()
        return [dict(r) for r in rows]

    def log_event(
        self,
        event_type: str,
        model_id: str,
        version: Optional[int],
        model_hash: Optional[str],
        result: str,
        blockchain_tx: Optional[str] = None,
        notes: Optional[str] = None
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO audit_log
                   (event_type, model_id, version, model_hash, result,
                    blockchain_tx, notes, occurred_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (event_type, model_id, version, model_hash,
                 result, blockchain_tx, notes, now)
            )

    def get_audit_log(self, model_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        with self._conn() as conn:
            if model_id:
                rows = conn.execute(
                    "SELECT * FROM audit_log WHERE model_id=? ORDER BY occurred_at DESC LIMIT ?",
                    (model_id, limit)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM audit_log ORDER BY occurred_at DESC LIMIT ?",
                    (limit,)
                ).fetchall()
        return [dict(r) for r in rows]
