from __future__ import annotations

from datetime import datetime, timezone
from email.message import EmailMessage
import smtplib

from quantforge_mcp.config import MCPSettings
from quantforge_mcp.schemas.monitor import SignalInfo


def _direction_label(direction: int) -> str:
    if direction > 0:
        return "做多 (+1)"
    if direction < 0:
        return "做空 (-1)"
    return "平仓 (0)"


class EmailNotifier:
    def __init__(self, settings: MCPSettings) -> None:
        self._settings = settings

    def _recipients(self, notify_to: str | None) -> list[str]:
        raw = (notify_to or self._settings.notify_to or "").strip()
        if not raw:
            return []
        return [addr.strip() for addr in raw.split(",") if addr.strip()]

    def send(
        self,
        *,
        strategy_name: str,
        signals: list[SignalInfo],
        notify_to: str | None = None,
    ) -> None:
        if not signals:
            return

        host = (self._settings.smtp_host or "").strip()
        recipients = self._recipients(notify_to)
        if not host:
            raise RuntimeError("SMTP not configured: set QUANTFORGE_SMTP_HOST")
        if not recipients:
            raise RuntimeError("no recipients: set QUANTFORGE_NOTIFY_TO or pass notify_to")
        sender = (self._settings.notify_from or self._settings.smtp_user or "").strip()
        if not sender:
            raise RuntimeError("no sender: set QUANTFORGE_NOTIFY_FROM or QUANTFORGE_SMTP_USER")

        lines = [
            f"策略: {strategy_name}",
            f"扫描时间 (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
            f"信号数量: {len(signals)}",
            "",
        ]
        for idx, sig in enumerate(signals, start=1):
            lines.extend(
                [
                    f"--- 信号 {idx} ---",
                    f"标的: {sig.symbol}",
                    f"方向: {_direction_label(sig.direction)}",
                    f"强度: {sig.strength:.4f}",
                    f"策略 ID: {sig.strategy_id}",
                    f"Bar 日期: {sig.bar_date}",
                    f"收盘价: {sig.close:.4f}",
                    "",
                ]
            )

        msg = EmailMessage()
        msg["Subject"] = f"[QuantForge] 策略信号: {strategy_name} ({len(signals)} 条)"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content("\n".join(lines).strip())

        with smtplib.SMTP(host, int(self._settings.smtp_port)) as smtp:
            if self._settings.smtp_use_tls:
                smtp.starttls()
            user = (self._settings.smtp_user or "").strip()
            password = self._settings.smtp_password or ""
            if user:
                smtp.login(user, password)
            smtp.send_message(msg)
