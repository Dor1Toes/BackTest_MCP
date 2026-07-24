from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import uuid4


class JobRepository:
    def __init__(self, conn_factory) -> None:
        self._conn_factory = conn_factory

    def create_job(self, *, job_type: str, config: dict, strategy_code: str | None = None) -> str:
        job_id = uuid4().hex[:12]
        sql = """
        INSERT INTO jobs(job_id, status, job_type, config_json, strategy_code, created_at)
        VALUES(?, 'running', ?, ?, ?, ?)
        """
        with self._conn_factory() as conn:
            conn.execute(sql, (job_id, job_type, json.dumps(config, ensure_ascii=False), strategy_code, datetime.utcnow().isoformat()))
            conn.commit()
        return job_id

    def update_job(
        self,
        job_id: str,
        *,
        status: str,
        error_message: str | None = None,
        summary: dict[str, Any] | None = None,
    ) -> None:
        sql = """
        UPDATE jobs
        SET status = ?, error_message = ?, summary_json = ?, finished_at = ?
        WHERE job_id = ?
        """
        summary_json = json.dumps(summary, ensure_ascii=False) if summary is not None else None
        with self._conn_factory() as conn:
            conn.execute(sql, (status, error_message, summary_json, datetime.utcnow().isoformat(), job_id))
            conn.commit()

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        sql = "SELECT * FROM jobs WHERE job_id = ?"
        with self._conn_factory() as conn:
            row = conn.execute(sql, (job_id,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["config_json"] = json.loads(item["config_json"]) if item.get("config_json") else {}
        item["summary_json"] = json.loads(item["summary_json"]) if item.get("summary_json") else None
        return item

    def list_jobs(self, *, limit: int = 50, status: str | None = None) -> list[dict[str, Any]]:
        limit = max(1, min(int(limit), 500))
        if status:
            sql = """
            SELECT job_id, status, job_type, config_json, error_message, summary_json, created_at, finished_at
            FROM jobs
            WHERE status = ?
            ORDER BY created_at DESC
            LIMIT ?
            """
            args: tuple[Any, ...] = (status, limit)
        else:
            sql = """
            SELECT job_id, status, job_type, config_json, error_message, summary_json, created_at, finished_at
            FROM jobs
            ORDER BY created_at DESC
            LIMIT ?
            """
            args = (limit,)
        with self._conn_factory() as conn:
            rows = conn.execute(sql, args).fetchall()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            item["config_json"] = json.loads(item["config_json"]) if item.get("config_json") else {}
            item["summary_json"] = json.loads(item["summary_json"]) if item.get("summary_json") else None
            items.append(item)
        return items
