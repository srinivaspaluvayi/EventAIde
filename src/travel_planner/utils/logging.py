from __future__ import annotations

import logging
from pathlib import Path
import re


_KEY_VALUE_PATTERN = re.compile(
    r'(?i)(\b(?:api[_-]?key|apikey|authorization|bearer|token|access[_-]?token|secret)\b'
    r'(?:\s*[:=]\s*|"\s*:\s*"|\'\s*:\s*\'))'
    r'([^\s&,"\'}]+)'
)
_OPENAI_KEY_PATTERN = re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")


def _redact_text(text: str) -> str:
    redacted = _KEY_VALUE_PATTERN.sub(r"\1***REDACTED***", text)
    redacted = _OPENAI_KEY_PATTERN.sub("***REDACTED***", redacted)
    # Simpler explicit pass for common URL query args.
    redacted = re.sub(r"(?i)([?&](?:api[_-]?key|apikey|token|access_token)=)[^&\s]+", r"\1***REDACTED***", redacted)
    return redacted


class _RedactingFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        rendered = super().format(record)
        return _redact_text(rendered)


def get_logger(name: str = "travel_planner") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "travel_planner.log", encoding="utf-8")
        formatter = _RedactingFormatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger

