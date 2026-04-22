from __future__ import annotations

import logging
from pathlib import Path


def get_logger(name: str = "travel_planner") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_dir = Path("logs")
        log_dir.mkdir(parents=True, exist_ok=True)
        handler = logging.FileHandler(log_dir / "travel_planner.log", encoding="utf-8")
        formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger

