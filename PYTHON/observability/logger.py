"""
logger.py — Structured JSON logging (ELK-ready)
Her log satiri: timestamp, level, service, trace_id, message, context
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredLogFormatter(logging.Formatter):
    """JSON formatli log uretir."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "trace_id": getattr(record, "trace_id", None),
            "agent": getattr(record, "agent", None),
            "symbol": getattr(record, "symbol", None),
            "context": getattr(record, "context", None),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_entry, ensure_ascii=False, default=str)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """Yapilandirilmis logger uretir."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(level)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(StructuredLogFormatter())
    logger.addHandler(handler)
    return logger


class AuditLogger:
    """Degistirilemez audit log: emir, risk karari, kill switch tetiklenmesi."""

    def __init__(self, logger: logging.Logger = None):
        self.logger = logger or get_logger("anatoliax.audit")

    def log_order(self, order_id: str, symbol: str, side: str, size: float, price: float, status: str, trace_id: str = ""):
        self.logger.info(
            "ORDER_EVENT",
            extra={
                "trace_id": trace_id,
                "symbol": symbol,
                "agent": "execution",
                "context": {
                    "order_id": order_id,
                    "side": side,
                    "size": size,
                    "price": price,
                    "status": status,
                },
            }
        )

    def log_risk_event(self, event_type: str, reason: str, trace_id: str = ""):
        self.logger.warning(
            "RISK_EVENT",
            extra={
                "trace_id": trace_id,
                "agent": "risk",
                "context": {"event_type": event_type, "reason": reason},
            }
        )

    def log_kill_switch(self, reason: str, capital: float, trace_id: str = ""):
        self.logger.critical(
            "KILL_SWITCH",
            extra={
                "trace_id": trace_id,
                "agent": "risk",
                "context": {"reason": reason, "capital": capital},
            }
        )
