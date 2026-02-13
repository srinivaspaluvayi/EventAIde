"""City name spelling correction using Ollama."""
import json
import re

import ollama


def get_city(city):
    system_m = "Correct the following city name for spelling errors and output only the most likely city name:\n"
    system_m += "For example: input :  naw yorkk, output: new york\n"
    system_m += "Do NOT explain your answer. Do NOT show any thoughts. Output ONLY the corrected city name.\n"
    system_m += "Your response should be in JSON format like {'corrected_city':city}"
    system_p = [{"role": "system", "content": system_m}]

    auto_corrections_model = "llama3.2:latest"

    messages = system_p + [{"role": "user", "content": city}]
    response = ollama.chat(model=auto_corrections_model, messages=messages)
    city = response["message"]["content"]
    match = re.search(r"\{.*\}", city)
    if match:
        try:
            data = json.loads(match.group(0))
            return data.get("corrected_city", "").strip()
        except json.JSONDecodeError:
            pass
    return ""
