from __future__ import annotations
from pathlib import Path
from typing import Any

from codegen import validate_strategy_code
from config import MCPSettings
from db.repositories import ArtifactRepository, JobRepository
from sandbox import run_backtest_in_sandbox
from schemas.strategy import BacktestConfig
from services.data_service import DataService


class BacktestService:
    def __init__(
        self,
        *,
        settings: MCPSettings,
        workspace_root: Path,
        data_service: DataService,
        job_repo: JobRepository,
        artifact_repo: ArtifactRepository,
    ) -> None:
        self._settings = settings
        self._workspace_root = workspace_root
        self._data_service = data_service
        self._job_repo = job_repo
        self._artifact_repo = artifact_repo

    def run_dynamic(self, *, code: str, config: BacktestConfig) -> dict[str, Any]:
        validation = validate_strategy_code(code).to_dict()
        if not validation["valid"]:
            return {"ok": False, "validation": validation}

        job_id = self._job_repo.create_job(job_type="dynamic", config=config.model_dump(), strategy_code=code)
        try:
            for symbol in config.symbols:
                self._data_service.get_ohlcv(symbol, config.start, config.end)
            payload = run_backtest_in_sandbox(
                settings=self._settings,
                workspace_root=self._workspace_root,
                job_id=job_id,
                code=code,
                config=config.model_dump(),
            )
            summary = {
                "job_id": job_id,
                "status": "done",
                "symbols": payload.get("symbols", config.symbols),
                # Keep backward compatibility for clients still reading "symbol".
                "symbol": (payload.get("symbols") or config.symbols)[0],
                "strategy_name": config.name,
                "metrics": payload.get("metrics", {}),
                "artifact_id": job_id,
            }
            self._job_repo.update_job(job_id, status="done", summary=summary)
            self._artifact_repo.add_artifact(job_id=job_id, kind="strategy_code", path=str((self._settings.artifacts_abspath() / job_id / "strategy.py")))
            self._artifact_repo.add_artifact(job_id=job_id, kind="stdout", path=str((self._settings.artifacts_abspath() / job_id / "stdout.txt")))
            self._artifact_repo.add_artifact(job_id=job_id, kind="stderr", path=str((self._settings.artifacts_abspath() / job_id / "stderr.txt")))
            if payload.get("equity_curve_path"):
                self._artifact_repo.add_artifact(job_id=job_id, kind="equity_curve", path=payload["equity_curve_path"])
            if payload.get("trades_path"):
                self._artifact_repo.add_artifact(job_id=job_id, kind="trades", path=payload["trades_path"])
            return {"ok": True, "job_id": job_id, "status": "done", "result": summary}
        except Exception as exc:
            self._job_repo.update_job(job_id, status="failed", error_message=str(exc))
            return {"ok": False, "job_id": job_id, "status": "failed", "error": str(exc), "validation": validation}

    def get_result(self, job_id: str) -> dict[str, Any]:
        row = self._job_repo.get_job(job_id)
        if row is None:
            return {"ok": False, "error": f"job '{job_id}' not found"}
        return {
            "ok": True,
            "job_id": row["job_id"],
            "status": row["status"],
            "job_type": row["job_type"],
            "error_message": row.get("error_message"),
            "result": row.get("summary_json"),
        }

    def get_artifacts(self, job_id: str, kind: str | None = None) -> dict[str, Any]:
        return {"ok": True, "job_id": job_id, "artifacts": self._artifact_repo.list_artifacts(job_id, kind)}

    def list_jobs(self, *, limit: int = 50, status: str = "") -> dict[str, Any]:
        rows = self._job_repo.list_jobs(limit=limit, status=(status or None))
        jobs: list[dict[str, Any]] = []
        for row in rows:
            config = row.get("config_json") or {}
            summary = row.get("summary_json") or {}
            metrics = summary.get("metrics") or {}
            jobs.append(
                {
                    "job_id": row["job_id"],
                    "status": row["status"],
                    "job_type": row["job_type"],
                    "strategy_name": summary.get("strategy_name") or config.get("name"),
                    "symbols": summary.get("symbols") or config.get("symbols", []),
                    "start": config.get("start"),
                    "end": config.get("end"),
                    "created_at": row.get("created_at"),
                    "finished_at": row.get("finished_at"),
                    "error_message": row.get("error_message"),
                    "total_return": metrics.get("total_return"),
                    "max_drawdown": metrics.get("max_drawdown"),
                    "n_trades": metrics.get("n_trades"),
                }
            )
        return {"ok": True, "count": len(jobs), "jobs": jobs}
