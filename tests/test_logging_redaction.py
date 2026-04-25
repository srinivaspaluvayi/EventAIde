from travel_planner.utils.logging import _redact_text


def test_redacts_common_key_patterns() -> None:
    raw = "apiKey=abc123 token: xyz789 Authorization=Bearer-raw OPENAI=sk-proj-abcdefghijklmnop"
    out = _redact_text(raw)
    assert "abc123" not in out
    assert "xyz789" not in out
    assert "Bearer-raw" not in out
    assert "sk-proj-abcdefghijklmnop" not in out
    assert "***REDACTED***" in out

