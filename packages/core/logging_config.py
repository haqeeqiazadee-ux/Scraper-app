"""
Structured logging configuration for the AI Scraping Platform.

Uses Python's standard logging with JSON formatting.
Each log record includes: timestamp, level, service, correlation_id, tenant_id, message.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from typing import Optional


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    def __init__(self, service_name: str = "scraper-platform") -> None:
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "service": self.service_name,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "tenant_id"):
            log_entry["tenant_id"] = record.tenant_id
        if hasattr(record, "task_id"):
            log_entry["task_id"] = record.task_id

        # Add any extra dict passed via `extra={}` in logging calls
        for key in ("url", "domain", "lane", "status", "duration_ms",
                     "items", "confidence", "error", "proxy", "session_id",
                     "queue", "msg_id", "key", "size", "content_type",
                     "solver", "cost", "attempt", "model", "count",
                     "seconds", "reason", "depth"):
            if hasattr(record, key):
                log_entry[key] = getattr(record, key)

        # Add exception info
        if record.exc_info and record.exc_info[1]:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


def configure_logging(
    service_name: str = "scraper-platform",
    level: str = "INFO",
    json_output: bool = True,
) -> None:
    """Configure structured logging for the application."""
    root = logging.getLogger()
    root.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove existing handlers
    root.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    if json_output:
        handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ))

    root.addHandler(handler)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
