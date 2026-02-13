"""Ticketmaster Discovery API: fetches event data for the app and MCP server."""
import json
import os
from collections import defaultdict

import requests
from dotenv import load_dotenv


def _load_env():
    load_dotenv()
    key = os.getenv("TICKETMASTER_API_KEY")
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    return key, url


def get_events_helper(
    city,
    size=200,
    state_code=None,
    classification_name=None,
    keyword=None,
    start_date=None,
    end_date=None,
):
    """Fetch events from Ticketmaster. Optional: state_code, classification_name, keyword, dates."""
    api_key, base_url = _load_env()
    params = {"apikey": api_key, "city": city, "size": size, "countryCode": "US"}
    if state_code:
        params["stateCode"] = state_code
    if classification_name:
        params["classificationName"] = classification_name
    if keyword:
        params["keyword"] = keyword
    if start_date:
        params["startDateTime"] = f"{start_date}T00:00:00Z"
    if end_date:
        params["endDateTime"] = f"{end_date}T23:59:59Z"
    response = requests.get(base_url, params=params)
    response.raise_for_status()
    data = response.json()
    if "_embedded" not in data:
        return []
    events = data.get("_embedded", []).get("events", [])

    out = []
    for event in events:
        try:
            name = event.get("name")
            if not name:
                continue
            date = event.get("dates", {}).get("start", {}).get("localDate") or ""
            time_obj = event.get("dates", {}).get("start", {}).get("localTime")
            if isinstance(time_obj, str):
                time = time_obj
            elif isinstance(time_obj, dict):
                h = time_obj.get("hourOfDay", 0)
                m = time_obj.get("minuteOfHour", 0)
                time = f"{h:02d}:{m:02d}:00" if (h or m) else ""
            else:
                time = ""
            venues = event.get("_embedded", {}).get("venues") or []
            if not venues:
                continue
            venue = venues[0]
            venue_name = venue.get("name") or "Unknown Venue"
            address = venue.get("address", {}).get("line1") or ""
            v_city = venue.get("city", {}).get("name") if isinstance(venue.get("city"), dict) else (venue.get("city") or "")
            state_obj = venue.get("state")
            state = state_obj.get("name", "") if isinstance(state_obj, dict) else (state_obj or "")

            event_details = {
                "name": name,
                "date": date,
                "time": time if isinstance(time, str) else "",
                "venue": {"name": venue_name, "address": address, "city": v_city, "state": state},
            }
            classifications = event.get("classifications")
            if classifications and isinstance(classifications, list) and len(classifications) > 0:
                c = classifications[0]
                event_details["classification"] = {
                    "segment": c.get("segment", {}).get("name", "N/A"),
                    "genre": c.get("genre", {}).get("name", "N/A"),
                    "subgenre": c.get("subGenre", {}).get("name", "N/A"),
                }
            else:
                event_details["classification"] = {"segment": "Other", "genre": "General", "subgenre": "N/A"}
            out.append(event_details)
        except Exception:
            continue
    return out


def _segment_events(events):
    segmented = defaultdict(lambda: defaultdict(list))
    for event in events:
        segment = event.get("classification", {}).get("segment", "Unknown")
        genre = event.get("classification", {}).get("genre", "Unknown")
        compact = event.copy()
        if "classification" in event and "subgenre" in event["classification"]:
            compact["subgenre"] = event["classification"].get("subgenre")
        compact.pop("classification", None)
        segmented[segment][genre].append(compact)
    result = json.loads(json.dumps(segmented))
    result.pop("Undefined", None)
    return result


def get_all_events(city, state_code=None):
    """All events in city, grouped by segment and genre. For app / get_all_events tool."""
    events = get_events_helper(city, state_code=state_code)
    return _segment_events(events)


def get_music_events(city, state_code=None, keyword=None, start_date=None, end_date=None):
    events = get_events_helper(
        city, state_code=state_code, classification_name="Music",
        keyword=keyword, start_date=start_date, end_date=end_date,
    )
    return _segment_events(events)


def get_sports_events(city, state_code=None, keyword=None, start_date=None, end_date=None):
    events = get_events_helper(
        city, state_code=state_code, classification_name="Sports",
        keyword=keyword, start_date=start_date, end_date=end_date,
    )
    return _segment_events(events)


def get_concerts(city, state_code=None, keyword=None, start_date=None, end_date=None):
    events = get_events_helper(
        city, state_code=state_code, classification_name="Music",
        keyword=keyword or "concert", start_date=start_date, end_date=end_date,
    )
    return _segment_events(events)


def get_film_events(city, state_code=None, keyword=None, start_date=None, end_date=None):
    events = get_events_helper(
        city, state_code=state_code, classification_name="Film",
        keyword=keyword, start_date=start_date, end_date=end_date,
    )
    return _segment_events(events)


def get_events_by_interests(city, interests, state_code=None, max_events=10):
    """Fetch events for city filtered by interests ('sports', 'music', 'movies'). Returns flat list, max_events total."""
    interest_set = {s.strip().lower() for s in interests if s}
    fetchers = []
    if "sports" in interest_set:
        fetchers.append(("Sports", get_sports_events))
    if "music" in interest_set:
        fetchers.append(("Music", get_music_events))
    if "movies" in interest_set or "film" in interest_set:
        fetchers.append(("Film", get_film_events))
    if not fetchers:
        events = get_events_helper(city, state_code=state_code)
        return events[:max_events]
    seen_names = set()
    flat = []
    for _label, get_events_fn in fetchers:
        if len(flat) >= max_events:
            break
        try:
            segmented = get_events_fn(city, state_code=state_code)
        except Exception:
            continue
        for segment, genres in segmented.items():
            if not isinstance(genres, dict):
                continue
            for genre, evs in genres.items():
                for e in evs:
                    if len(flat) >= max_events:
                        break
                    name = e.get("name") or ""
                    if name and name not in seen_names:
                        seen_names.add(name)
                        flat.append(e)
    return flat[:max_events]
