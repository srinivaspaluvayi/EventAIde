from __future__ import annotations

import json
from typing import Any, Dict

from openai import OpenAI


def extract_json(raw_text: str) -> Dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        text = text.replace("json\n", "", 1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model output.")
    return json.loads(text[start : end + 1])


class SmallModelClient:
    """Compact client wrapper tuned for small-model reliability."""

    def __init__(self, api_key: str, model: str) -> None:
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def run_json(self, system_prompt: str, user_prompt: str, max_tokens: int = 700) -> Dict[str, Any]:
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_output_tokens=max_tokens,
        )
        return extract_json(response.output_text)

