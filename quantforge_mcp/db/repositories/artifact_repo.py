from __future__ import annotations

from datetime import datetime
from typing import Any


class ArtifactRepository:
    def __init__(self, conn_factory) -> None:
        self._conn_factory = conn_factory

    def add_artifact(self, *, job_id: str, kind: str, path: str) -> None:
        sql = "INSERT INTO artifacts(job_id, kind, path, created_at) VALUES(?, ?, ?, ?)"
        with self._conn_factory() as conn:
            conn.execute(sql, (job_id, kind, path, datetime.utcnow().isoformat()))
            conn.commit()

    def list_artifacts(self, job_id: str, kind: str | None = None) -> list[dict[str, Any]]:
        if kind:
            sql = "SELECT id, job_id, kind, path, created_at FROM artifacts WHERE job_id = ? AND kind = ? ORDER BY id"
            args = (job_id, kind)
        else:
            sql = "SELECT id, job_id, kind, path, created_at FROM artifacts WHERE job_id = ? ORDER BY id"
            args = (job_id,)
        with self._conn_factory() as conn:
            rows = conn.execute(sql, args).fetchall()
        return [dict(r) for r in rows]
