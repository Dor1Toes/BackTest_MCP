from __future__ import annotations

from pathlib import Path

import pandas as pd

from quantforge_mcp.quantforge_stock.analytics.tearsheet import tearsheet_markdown

from quantforge_mcp.db.repositories import ArtifactRepository


class ReportService:
    def __init__(self, artifact_repo: ArtifactRepository) -> None:
        self._artifact_repo = artifact_repo

    def generate(self, *, job_id: str, title: str = "") -> dict:
        artifacts = self._artifact_repo.list_artifacts(job_id, kind="equity_curve")
        if not artifacts:
            return {"ok": False, "error": f"equity curve artifact not found for job '{job_id}'"}
        equity_path = Path(artifacts[-1]["path"])
        if not equity_path.exists():
            return {"ok": False, "error": f"equity curve file missing: {equity_path}"}

        frame = pd.read_csv(equity_path)
        if "date" in frame.columns:
            frame["date"] = pd.to_datetime(frame["date"])
            frame = frame.set_index("date")
        elif frame.columns[0].lower() in {"timestamp", "index"}:
            frame[frame.columns[0]] = pd.to_datetime(frame[frame.columns[0]])
            frame = frame.set_index(frame.columns[0])
        equity_col = "equity" if "equity" in frame.columns else frame.columns[-1]
        equity = frame[equity_col]

        report_title = title or f"Backtest {job_id}"
        content = tearsheet_markdown(equity, report_title)
        report_path = equity_path.parent / "report.md"
        report_path.write_text(content, encoding="utf-8")
        self._artifact_repo.add_artifact(job_id=job_id, kind="report_markdown", path=str(report_path))

        return {
            "ok": True,
            "job_id": job_id,
            "title": report_title,
            "format": "markdown",
            "path": str(report_path),
            "content": content,
        }
