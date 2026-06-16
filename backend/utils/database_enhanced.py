import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any


class DatabaseEnhanced:
    def __init__(self, db_path="sentinelai_enhanced.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id    TEXT NOT NULL,
                model_name  TEXT NOT NULL,
                version     INTEGER NOT NULL,
                file_path   TEXT NOT NULL,
                model_hash  TEXT NOT NULL,
                file_size   INTEGER,
                tx_hash     TEXT,
                description TEXT,
                owner       TEXT,
                tags        TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(model_id, version)
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_log (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                event_type   TEXT NOT NULL,
                model_id     TEXT,
                version      INTEGER,
                model_hash   TEXT,
                result       TEXT,
                blockchain_tx TEXT,
                notes        TEXT
            )
        """)

        # Indexes to make search and lookups fast
        cur.execute("CREATE INDEX IF NOT EXISTS idx_model_id   ON models(model_id)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_owner      ON models(owner)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_created_at ON models(created_at DESC)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_audit      ON audit_log(model_id)")

        conn.commit()
        conn.close()

    def register_model(
        self,
        model_id: str,
        model_name: str,
        version: int,
        file_path: str,
        model_hash: str,
        file_size: int,
        tx_hash: Optional[str] = None,
        description: Optional[str] = None,
        owner: Optional[str] = None,
        tags: Optional[List[str]] = None
    ):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO models
            (model_id, model_name, version, file_path, model_hash,
             file_size, tx_hash, description, owner, tags)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_id, model_name, version, file_path, model_hash,
            file_size, tx_hash, description, owner,
            json.dumps(tags) if tags else None
        ))
        conn.commit()
        conn.close()

    def get_model(self, model_id: str, version: Optional[int] = None) -> Optional[Dict]:
        """Returns the requested version, or the latest if version is None."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if version:
            cur.execute(
                "SELECT * FROM models WHERE model_id = ? AND version = ?",
                (model_id, version)
            )
        else:
            cur.execute(
                "SELECT * FROM models WHERE model_id = ? ORDER BY version DESC LIMIT 1",
                (model_id,)
            )

        row = cur.fetchone()
        conn.close()

        if not row:
            return None

        result = dict(row)
        if result.get("tags"):
            result["tags"] = json.loads(result["tags"])
        return result

    def get_model_versions(self, model_id: str) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM models WHERE model_id = ? ORDER BY version ASC",
            (model_id,)
        )
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            r = dict(row)
            if r.get("tags"):
                r["tags"] = json.loads(r["tags"])
            results.append(r)
        return results

    def list_models(
        self,
        search: Optional[str] = None,
        tag: Optional[str] = None,
        owner: Optional[str] = None
    ) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        query = """
            SELECT model_id, model_name, description, owner, tags,
                   MAX(version) as latest_version,
                   MAX(created_at) as last_updated
            FROM models
            WHERE 1=1
        """
        params = []

        if search:
            query += " AND (model_id LIKE ? OR model_name LIKE ? OR description LIKE ?)"
            p = f"%{search}%"
            params.extend([p, p, p])

        if owner:
            query += " AND owner LIKE ?"
            params.append(f"%{owner}%")

        if tag:
            query += " AND tags LIKE ?"
            params.append(f"%{tag}%")

        query += " GROUP BY model_id ORDER BY last_updated DESC"

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        results = []
        for row in rows:
            m = dict(row)
            if m.get("tags"):
                try:
                    m["tags"] = json.loads(m["tags"])
                except Exception:
                    m["tags"] = []
            results.append(m)
        return results

    def log_event(
        self,
        event_type: str,
        model_id: Optional[str] = None,
        version: Optional[int] = None,
        model_hash: Optional[str] = None,
        result: Optional[str] = None,
        blockchain_tx: Optional[str] = None,
        notes: Optional[str] = None
    ):
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO audit_log
            (event_type, model_id, version, model_hash, result, blockchain_tx, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (event_type, model_id, version, model_hash, result, blockchain_tx, notes))
        conn.commit()
        conn.close()

    def get_audit_log(self, model_id: Optional[str] = None, limit: int = 100) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        if model_id:
            cur.execute(
                "SELECT * FROM audit_log WHERE model_id = ? ORDER BY timestamp DESC LIMIT ?",
                (model_id, limit)
            )
        else:
            cur.execute(
                "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            )

        rows = cur.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_statistics(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        cur.execute("SELECT COUNT(DISTINCT model_id) as total FROM models")
        total_models = cur.fetchone()["total"]

        cur.execute("SELECT COUNT(*) as total FROM models")
        total_versions = cur.fetchone()["total"]

        cur.execute("""
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN result = 'PASS' THEN 1 ELSE 0 END) as passed,
                SUM(CASE WHEN result = 'FAIL' THEN 1 ELSE 0 END) as failed
            FROM audit_log
            WHERE event_type = 'VERIFY'
        """)
        v = dict(cur.fetchone())

        cur.execute("SELECT COUNT(*) as total FROM models WHERE tx_hash IS NOT NULL")
        blockchain_tx = cur.fetchone()["total"]

        conn.close()

        success_rate = 0
        if v["total"] and v["total"] > 0:
            success_rate = (v["passed"] / v["total"]) * 100

        return {
            "total_models": total_models,
            "total_versions": total_versions,
            "total_verifications": v["total"],
            "successful_verifications": v["passed"],
            "failed_verifications": v["failed"],
            "success_rate": success_rate,
            "blockchain_transactions": blockchain_tx
        }
