from __future__ import annotations

from datetime import date
import json

from quantforge_mcp.codegen import validate_strategy_code as ast_validate_strategy_code
from quantforge_mcp.schemas.strategy import BacktestConfig, BacktestConfigValidationResult
from quantforge_mcp.services.backtest_service import BacktestService
from quantforge_mcp.services.report_service import ReportService


def register_backtest_tools(mcp, backtest_service: BacktestService, report_service: ReportService) -> None:
    @mcp.tool()
    def validate_strategy_code(code: str) -> dict:
        return ast_validate_strategy_code(code).to_dict()

    @mcp.tool()
    def validate_backtest_config(config_json: str) -> dict:
        warnings: list[str] = []
        errors: list[str] = []
        try:
            config = BacktestConfig(**json.loads(config_json))
        except Exception as exc:
            result = BacktestConfigValidationResult(valid=False, errors=[f"invalid config: {exc}"])
            return {"ok": False, "validation": result.model_dump()}

        if config.initial_capital <= 0:
            errors.append("initial_capital must be > 0")
        if config.commission < 0:
            errors.append("commission must be >= 0")
        if config.slippage < 0:
            errors.append("slippage must be >= 0")

        if config.start:
            try:
                date.fromisoformat(config.start)
            except ValueError:
                errors.append("start format must be YYYY-MM-DD")
        if config.end:
            try:
                date.fromisoformat(config.end)
            except ValueError:
                errors.append("end format must be YYYY-MM-DD")
        if config.start and config.end and config.start >= config.end:
            errors.append("start must be earlier than end")

        result = BacktestConfigValidationResult(valid=not errors, warnings=warnings, errors=errors)
        return {"ok": result.valid, "validation": result.model_dump()}

    @mcp.tool()
    def run_backtest_dynamic(code: str, config_json: str) -> dict:
        config = BacktestConfig(**json.loads(config_json))
        return backtest_service.run_dynamic(code=code, config=config)

    @mcp.tool()
    def get_backtest_result(job_id: str) -> dict:
        return backtest_service.get_result(job_id)

    @mcp.tool()
    def generate_backtest_report(job_id: str, title: str = "") -> dict:
        return report_service.generate(job_id=job_id, title=title)

    @mcp.tool()
    def get_backtest_artifacts(job_id: str, kind: str = "") -> dict:
        return backtest_service.get_artifacts(job_id=job_id, kind=(kind or None))
