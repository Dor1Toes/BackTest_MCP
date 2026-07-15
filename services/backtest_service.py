from __future__ import annotations
from pathlib import Path
from typing import Any

from quantforge_mcp.codegen import validate_strategy_code
from quantforge_mcp.config import MCPSettings
from quantforge_mcp.db.repositories import ArtifactRepository, JobRepository
from quantforge_mcp.sandbox import run_backtest_in_sandbox
from quantforge_mcp.schemas.strategy import BacktestConfig
from quantforge_mcp.services.data_service import DataService


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
            symbol = config.symbols[0]
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
                "symbol": payload.get("symbol", symbol),
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
