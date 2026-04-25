from __future__ import annotations

import re
from typing import Final

# Major US airport IATA codes (US states + DC). Keep this curated list focused
# on practical consumer routes instead of every possible FAA location code.
US_IATA_CODES: Final[set[str]] = {
    "ATL", "AUS", "BNA", "BOS", "BWI", "CLT", "DCA", "DEN", "DFW", "DTW",
    "EWR", "FLL", "HNL", "IAD", "IAH", "JFK", "LAS", "LAX", "LGA", "MCI",
    "MCO", "MDW", "MIA", "MSP", "MSY", "OAK", "ONT", "ORD", "PDX", "PHL",
    "PHX", "PIT", "RDU", "SAN", "SAT", "SEA", "SFO", "SJC", "SLC", "SMF",
    "SNA", "STL", "TPA",
}


def normalize_us_iata(value: str | None) -> str:
    """Return a normalized US IATA code, or empty string."""
    if not value:
        return ""
    text = value.strip().upper()
    m = re.search(r"\b([A-Z]{3})\b", text)
    if not m:
        return ""
    code = m.group(1)
    return code if code in US_IATA_CODES else ""

