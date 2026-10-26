"""SQLite transactions coordinate API and workers, including approval and leases."""
from __future__ import annotations

import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable

from shared.contracts import RunRecord, TERMINAL, utcnow


class ConflictError(ValueError):
    pass


class RunRepository:
    def __init__(self, workspace: Path):
        workspace.mkdir(parents=True, exist_ok=True)
        self.path = workspace / "runs.sqlite"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY, status TEXT NOT NULL, created TEXT NOT NULL,
                    payload TEXT NOT NULL, owner TEXT, lease REAL
                );
                CREATE INDEX IF NOT EXISTS runs_status ON runs(status, created);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT NOT NULL,
                    time TEXT NOT NULL, stage TEXT NOT NULL, level TEXT NOT NULL,
                    message TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS events_run ON events(run_id, id);
            """)

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path, timeout=30)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except BaseException:
            db.rollback()
            raise
        finally:
            db.close()

    def create(self, record: RunRecord) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO runs(id,status,created,payload) VALUES (?,?,?,?)", (record.run_id, record.status, record.created_at, record.model_dump_json()))

    def get(self, run_id: str) -> RunRecord:
        with self.connection() as db:
            row = db.execute("SELECT payload FROM runs WHERE id=?", (run_id,)).fetchone()
        if row is None:
            raise KeyError(run_id)
        return RunRecord.model_validate_json(row[0])

    def list(self, limit=50, offset=0) -> tuple[list[RunRecord], int]:
        with self.connection() as db:
            rows = db.execute("SELECT payload FROM runs ORDER BY created DESC LIMIT ? OFFSET ?", (limit, offset)).fetchall()
            count = db.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
        return [RunRecord.model_validate_json(row[0]) for row in rows], count

    def update(self, run_id: str, mutate: Callable[[RunRecord], None], *, owner: str | None = None) -> RunRecord:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT payload,owner,status FROM runs WHERE id=?", (run_id,)).fetchone()
            if row is None:
                raise KeyError(run_id)
            if owner is not None and (row["owner"] != owner or row["status"] == "cancelled"):
                raise ConflictError("Run ownership changed or the run was cancelled.")
            run = RunRecord.model_validate_json(row["payload"])
            mutate(run)
            run.updated_at = utcnow()
            # Revalidate nested changes before persistence.
            run = RunRecord.model_validate(run.model_dump())
            db.execute("UPDATE runs SET status=?,payload=? WHERE id=?", (run.status, run.model_dump_json(), run_id))
        return run

    def claim(self, owner: str, lease_seconds=60) -> RunRecord | None:
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            # Interrupted computations are explicitly failed; approval checkpoints remain resumable.
            stale = db.execute("SELECT id,payload FROM runs WHERE status='running' AND lease < ?", (time.time(),)).fetchall()
            for row in stale:
                run = RunRecord.model_validate_json(row["payload"])
                run.status = "failed"
                run.error = "The worker stopped responding. Start a new run; saved artifacts remain available."
                run.completed_at = run.updated_at = utcnow()
                if run.stage in run.agents:
                    run.agents[run.stage].status = "failed"
                db.execute("UPDATE runs SET status='failed',payload=?,owner=NULL WHERE id=?", (run.model_dump_json(), row["id"]))
            row = db.execute("SELECT payload FROM runs WHERE status='queued' AND owner IS NULL ORDER BY created LIMIT 1").fetchone()
            if row is None:
                return None
            run = RunRecord.model_validate_json(row[0])
            run.status = "running"
            run.started_at = run.started_at or utcnow()
            run.updated_at = utcnow()
            db.execute("UPDATE runs SET status='running',payload=?,owner=?,lease=? WHERE id=?", (run.model_dump_json(), owner, time.time() + lease_seconds, run.run_id))
        return run

    def heartbeat(self, run_id: str, owner: str, lease_seconds=60) -> bool:
        with self.connection() as db:
            cursor = db.execute("UPDATE runs SET lease=? WHERE id=? AND owner=? AND status='running'", (time.time() + lease_seconds, run_id, owner))
        return cursor.rowcount == 1

    def release(self, run_id: str, owner: str) -> None:
        with self.connection() as db:
            db.execute("UPDATE runs SET owner=NULL,lease=NULL WHERE id=? AND owner=?", (run_id, owner))

    def event(self, run_id: str, stage: str, message: str, level="info") -> None:
        with self.connection() as db:
            db.execute("INSERT INTO events(run_id,time,stage,level,message) VALUES(?,?,?,?,?)", (run_id, utcnow(), stage, level, message))

    def events(self, run_id: str, after=0) -> list[dict]:
        with self.connection() as db:
            rows = db.execute("SELECT id,time,stage,level,message FROM events WHERE run_id=? AND id>? ORDER BY id LIMIT 1000", (run_id, after)).fetchall()
        return [dict(row) for row in rows]
