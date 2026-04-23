from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List

import serpapi

from travel_planner.models.schemas import HotelOption, TravelProfile
from travel_planner.providers.serpapi_util import serpapi_search_api_error
from travel_planner.utils.logging import get_logger

_MAX_PROPERTIES_TO_SCAN = 40
_MAX_HOTELS = 5
_TIER_LABELS = ("Budget (low)", "Mid-range", "Premium (high)")


@dataclass
class SerpApiHotelProvider:
    """Google Hotels via SerpAPI [Search API](https://serpapi.com/search-api) with ``engine=google_hotels``."""

    api_key: str
    timeout_seconds: int = 15

    def __post_init__(self) -> None:
        self._log = get_logger("travel_planner.serpapi_hotels")
        self._client = serpapi.Client(api_key=self.api_key)

    def search_hotels(self, profile: TravelProfile) -> List[HotelOption]:
        if not self.api_key:
            return []
        params: dict[str, str | int] = {
            "engine": "google_hotels",
            "q": f"hotels in {profile.destination}",
            "check_in_date": str(profile.start_date),
            "check_out_date": str(profile.end_date),
            "adults": max(profile.group_size, 1),
            "currency": "USD",
        }
        try:
            payload = self._client.search(params, timeout=self.timeout_seconds)
        except serpapi.SerpApiError as exc:
            self._log.warning("SerpAPI hotel search failed: %s", exc)
            return []

        api_err = serpapi_search_api_error(payload)
        if api_err:
            self._log.warning("SerpAPI hotel search returned API error: %s", api_err)
            return []

        properties = payload.get("properties", [])
        if not isinstance(properties, list):
            return []

        candidates: list[tuple[HotelOption, float | None]] = []
        for item in properties[:_MAX_PROPERTIES_TO_SCAN]:
            if not isinstance(item, dict):
                continue
            opt = self._item_to_hotel_option(item)
            if opt is None:
                continue
            price = self._extract_sort_price(item)
            candidates.append((opt, price))

        return self._pick_five_across_tiers(candidates)

    def _item_to_hotel_option(self, item: dict) -> HotelOption | None:
        name = str(item.get("name", "")).strip()
        if not name:
            return None
        area = str(item.get("type", "Popular area")).strip()
        total_rate = item.get("total_rate", {}) if isinstance(item.get("total_rate"), dict) else {}
        price = str(total_rate.get("lowest", "")).strip()
        if not price:
            extracted_prices = item.get("extracted_hotel_class")
            price = f"${extracted_prices}" if extracted_prices else "See latest pricing"
        highlights: list[str] = []
        for key in ("overall_rating", "reviews", "location_rating"):
            value = item.get(key)
            if value not in (None, "", []):
                highlights.append(f"{key.replace('_', ' ').title()}: {value}")
        if not highlights:
            highlights = ["Check latest amenities and cancellation terms."]
        return HotelOption(
            name=name,
            area=area,
            price_range_usd=price,
            highlights=highlights[:4],
        )

    def _extract_sort_price(self, item: dict) -> float | None:
        """Numeric total (or proxy) for bucketing; None if unparseable."""
        tr = item.get("total_rate")
        if isinstance(tr, dict):
            for key in ("lowest", "extracted_lowest", "highest"):
                n = self._money_to_float(tr.get(key))
                if n is not None:
                    return n
        for key in ("extracted_price", "price", "gnb_price"):
            n = self._money_to_float(item.get(key))
            if n is not None:
                return n
        hc = item.get("extracted_hotel_class")
        if isinstance(hc, (int, float)) and 0 < float(hc) <= 5:
            return float(hc) * 120.0
        return None

    @staticmethod
    def _money_to_float(value: object) -> float | None:
        if value is None:
            return None
        if isinstance(value, (int, float)) and float(value) > 0:
            return float(value)
        if not isinstance(value, str):
            return None
        cleaned = re.sub(r"[^\d.]", "", value.replace(",", ""))
        if not cleaned:
            return None
        try:
            x = float(cleaned)
            return x if x > 0 else None
        except ValueError:
            return None

    def _pick_five_across_tiers(self, rows: list[tuple[HotelOption, float | None]]) -> List[HotelOption]:
        """Up to 5 hotels, preferring a mix of low / mid / high price within this SerpAPI result set."""
        if not rows:
            return []

        priced: list[tuple[float, HotelOption]] = []
        unpriced: list[HotelOption] = []
        seen_name: set[str] = set()
        for opt, p in rows:
            key = opt.name.strip().lower()
            if not key or key in seen_name:
                continue
            seen_name.add(key)
            if p is not None and p > 0:
                priced.append((p, opt))
            else:
                unpriced.append(opt)

        if not priced:
            return unpriced[:_MAX_HOTELS]

        priced.sort(key=lambda x: x[0])
        n = len(priced)
        i1 = max(1, n // 3)
        i2 = max(i1 + 1, (2 * n) // 3)
        low = priced[:i1]
        mid = priced[i1:i2]
        high = priced[i2:]
        regions: tuple[list[tuple[float, HotelOption]], ...] = (low, mid, high)

        picked: list[HotelOption] = []
        picked_keys: set[str] = set()
        ptrs = [0, 0, 0]

        def take_from(region_idx: int) -> HotelOption | None:
            reg = regions[region_idx]
            while ptrs[region_idx] < len(reg):
                _, opt = reg[ptrs[region_idx]]
                ptrs[region_idx] += 1
                k = opt.name.strip().lower()
                if k not in picked_keys:
                    picked_keys.add(k)
                    return self._with_tier_highlight(opt, _TIER_LABELS[region_idx])
            return None

        r = 0
        stagnant = 0
        while len(picked) < _MAX_HOTELS and stagnant < 12:
            before = len(picked)
            o = take_from(r % 3)
            if o:
                picked.append(o)
                stagnant = 0
            else:
                stagnant += 1
            r += 1

        if len(picked) < _MAX_HOTELS:
            for _, opt in priced:
                if len(picked) >= _MAX_HOTELS:
                    break
                k = opt.name.strip().lower()
                if k in picked_keys:
                    continue
                picked_keys.add(k)
                picked.append(opt)
        for opt in unpriced:
            if len(picked) >= _MAX_HOTELS:
                break
            k = opt.name.strip().lower()
            if k in picked_keys:
                continue
            picked_keys.add(k)
            picked.append(self._with_tier_highlight(opt, "Price not parsed (see rate text)"))

        return picked[:_MAX_HOTELS]

    @staticmethod
    def _with_tier_highlight(opt: HotelOption, tier_note: str) -> HotelOption:
        tier_line = f"Vs this search: {tier_note}"
        merged = [tier_line] + [h for h in opt.highlights if h != tier_line][:3]
        return HotelOption(
            name=opt.name,
            area=opt.area,
            price_range_usd=opt.price_range_usd,
            highlights=merged[:4],
        )
