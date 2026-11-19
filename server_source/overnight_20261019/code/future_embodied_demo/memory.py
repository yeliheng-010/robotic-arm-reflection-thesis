from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import List, Optional

from .models import MemoryEpisode


class MemoryStore:
    """Append-only episodic memory used by the deterministic cognitive backend."""

    def __init__(self, path: str | Path = ":memory:") -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute(
            """
            CREATE TABLE IF NOT EXISTS episodes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at REAL NOT NULL,
                signature TEXT NOT NULL,
                context_json TEXT NOT NULL,
                repair_json TEXT NOT NULL,
                outcome TEXT NOT NULL,
                task_id TEXT
            )
            """
        )
        self._connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_episode_signature ON episodes(signature, created_at DESC)"
        )
        self._connection.commit()

    def record(self, episode: MemoryEpisode) -> int:
        with self._lock:
            cursor = self._connection.execute(
                """
                INSERT INTO episodes(
                    created_at, signature, context_json, repair_json, outcome, task_id
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.created_at,
                    episode.signature,
                    json.dumps(episode.context, ensure_ascii=False, sort_keys=True),
                    json.dumps(episode.repair, ensure_ascii=False, sort_keys=True),
                    episode.outcome,
                    episode.task_id,
                ),
            )
            self._connection.commit()
            return int(cursor.lastrowid)

    def find(self, signature: str, limit: int = 5) -> List[MemoryEpisode]:
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM episodes
                WHERE signature = ?
                ORDER BY created_at DESC, id DESC
                LIMIT ?
                """,
                (signature, int(limit)),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def recent(self, limit: int = 20) -> List[MemoryEpisode]:
        with self._lock:
            rows = self._connection.execute(
                "SELECT * FROM episodes ORDER BY created_at DESC, id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        return [self._from_row(row) for row in rows]

    def count(self, signature: Optional[str] = None) -> int:
        with self._lock:
            if signature is None:
                row = self._connection.execute("SELECT COUNT(*) AS n FROM episodes").fetchone()
            else:
                row = self._connection.execute(
                    "SELECT COUNT(*) AS n FROM episodes WHERE signature = ?", (signature,)
                ).fetchone()
        return int(row["n"])

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    @staticmethod
    def _from_row(row: sqlite3.Row) -> MemoryEpisode:
        return MemoryEpisode(
            episode_id=int(row["id"]),
            created_at=float(row["created_at"]),
            signature=str(row["signature"]),
            context=json.loads(row["context_json"]),
            repair=json.loads(row["repair_json"]),
            outcome=str(row["outcome"]),
            task_id=row["task_id"],
        )
