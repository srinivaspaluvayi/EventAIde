"""Helpers for SerpAPI [Search API](https://serpapi.com/search-api) JSON responses."""

from __future__ import annotations


def serpapi_search_api_error(payload: object) -> str | None:
    """Return a message if the Search API reported failure (not transport-level).

    Documented JSON fields: ``search_metadata.status`` → ``Success`` or ``Error``;
    failed searches may include ``error``. See https://serpapi.com/search-api#api-results-json-results
    """
    if not isinstance(payload, dict):
        return "invalid JSON payload"
    top = payload.get("error")
    if top is not None and top != "":
        return str(top) if not isinstance(top, dict) else str(top.get("message", top))
    meta = payload.get("search_metadata")
    if isinstance(meta, dict) and meta.get("status") == "Error":
        return str(meta.get("error") or meta.get("json_endpoint") or "search_metadata.status=Error")
    return None
