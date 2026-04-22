from __future__ import annotations

from typing import List

from ddgs import DDGS


def web_search(query: str, max_results: int = 6) -> List[str]:
    snippets: List[str] = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            title = item.get("title", "").strip()
            body = item.get("body", "").strip()
            href = item.get("href", "").strip()
            if not any([title, body, href]):
                continue
            snippets.append(f"{title} | {body} | {href}".strip())
    return snippets

