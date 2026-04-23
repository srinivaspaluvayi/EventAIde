from travel_planner.utils.us_airports import normalize_us_iata


def test_normalize_us_iata_accepts_major_us_airports() -> None:
    assert normalize_us_iata(" lax ") == "LAX"
    assert normalize_us_iata("Flying to ORD soon") == "ORD"


def test_normalize_us_iata_rejects_non_us_codes() -> None:
    assert normalize_us_iata("CDG") == ""
    assert normalize_us_iata("NRT") == ""

