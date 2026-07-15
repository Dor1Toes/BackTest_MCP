from __future__ import annotations

import json
import subprocess
from pathlib import Path

from quantforge_mcp.config import MCPSettings


def run_backtest_in_sandbox(
    *,
    settings: MCPSettings,
    workspace_root: Path,
    job_id: str,
    code: str,
    config: dict,
) -> dict:
    job_dir = settings.artifacts_abspath() / job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    strategy_path = job_dir / "strategy.py"
    config_path = job_dir / "config.json"
    strategy_path.write_text(code, encoding="utf-8")
    config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

    worker_script = workspace_root / "quantforge_mcp" / "sandbox" / "worker" / "backtest_worker.py"
    cmd = [
        "python",
        str(worker_script),
        "--db",
        str(settings.db_abspath()),
        "--job-dir",
        str(job_dir),
    ]

    if settings.docker_enabled:
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            settings.sandbox_mem_limit,
            "--cpu-quota",
            str(settings.sandbox_cpu_quota),
            "-v",
            f"{settings.db_abspath()}:/sandbox/quantforge.db:ro",
            "-v",
            f"{job_dir}:/sandbox/job:rw",
            settings.docker_image,
            "--db",
            "/sandbox/quantforge.db",
            "--job-dir",
            "/sandbox/job",
        ]
        cmd = docker_cmd

    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=settings.sandbox_timeout_sec)
    (job_dir / "stdout.txt").write_text(proc.stdout or "", encoding="utf-8")
    (job_dir / "stderr.txt").write_text(proc.stderr or "", encoding="utf-8")

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or "sandbox worker failed")

    lines = [line.strip() for line in (proc.stdout or "").splitlines() if line.strip()]
    if not lines:
        raise RuntimeError("sandbox worker returned empty output")
    return json.loads(lines[-1])
