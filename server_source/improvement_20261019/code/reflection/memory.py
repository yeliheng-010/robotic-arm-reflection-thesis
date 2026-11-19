"""Store only corrections confirmed by independent physical evaluation."""
import json
from pathlib import Path
import sqlite3
import time

from .reflector import Parameters


class ExperienceMemory:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(path))
        self.conn.execute("""CREATE TABLE IF NOT EXISTS experiences (
            context TEXT, signature TEXT, parameters TEXT, causes TEXT,
            successes INTEGER DEFAULT 1, failures INTEGER DEFAULT 0, updated REAL,
            PRIMARY KEY(context, signature))""")
        self.conn.commit()

    def remember(self, context, reports, parameters, reflections):
        if not reports or not reflections:
            return
        signature = ",".join(sorted({r.error_type.value for r in reports}))
        self.conn.execute("""INSERT INTO experiences VALUES (?,?,?,?,1,0,?)
            ON CONFLICT(context,signature) DO UPDATE SET
            parameters=excluded.parameters, causes=excluded.causes,
            successes=successes+1, failures=0, updated=excluded.updated""",
            (context, signature, json.dumps(parameters.to_dict()),
             json.dumps([r.to_dict() for r in reflections], ensure_ascii=False), time.time()))
        self.conn.commit()

    def recall(self, context):
        rows = self.conn.execute("""SELECT signature,parameters,causes,successes,failures
            FROM experiences WHERE context=? AND successes>failures
            ORDER BY (1.0*successes/(successes+failures)) DESC,updated DESC""", (context,)).fetchall()
        for signature, params, causes, successes, failures in rows:
            try:
                validated = Parameters().updated(json.loads(params))
            except (ValueError, TypeError, json.JSONDecodeError):
                continue
            return {"signature": signature, "parameters": validated.to_dict(),
                    "causes": json.loads(causes), "successes": successes, "failures": failures}
        return None

    def feedback(self, context, signature, success):
        column = "successes" if success else "failures"
        self.conn.execute(f"UPDATE experiences SET {column}={column}+1,updated=? WHERE context=? AND signature=?",
                          (time.time(), context, signature))
        self.conn.commit()

    def close(self):
        self.conn.close()

    def checkpoint(self, path):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(".tmp")
        with sqlite3.connect(str(temporary)) as backup:
            self.conn.backup(backup)
        temporary.replace(path)

    def restore(self, path):
        with sqlite3.connect(f"file:{Path(path).resolve()}?mode=ro", uri=True) as backup:
            backup.backup(self.conn)
