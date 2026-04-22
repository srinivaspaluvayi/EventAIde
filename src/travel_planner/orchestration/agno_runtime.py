from __future__ import annotations

from typing import Optional


def agno_available() -> bool:
    try:
        import agno  # noqa: F401

        return True
    except Exception:
        return False


def runtime_note() -> Optional[str]:
    if agno_available():
        return "Agno is installed and used for orchestration scaffolding."
    return "Agno is not available in the current environment."

