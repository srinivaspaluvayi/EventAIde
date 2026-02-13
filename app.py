"""EventAIde: chat UI — city, then interests, then top 10 events in Markdown."""
import os
import re
from datetime import datetime

import gradio as gr
from dotenv import load_dotenv

from city_corrections import get_city
from eventaide_mcp.ticketmaster import get_events_by_interests

load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))

WELCOME = (
    "Hi! 👋 I'm EventAIde. **Which city** are you looking for events in? "
    "Just type the city name (e.g. New York, Los Angeles)."
)
INTERESTS_PROMPT = (
    "Got it, **{city}**! What are you interested in? "
    "Pick one or more: **sports**, **music**, **movies**."
)
TOP_N = 10


def _format_date(date_str: str) -> str:
    """Turn YYYY-MM-DD into a friendlier display (e.g. Sat, Mar 15)."""
    if not date_str or len(date_str) < 10:
        return date_str
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return d.strftime("%a, %b %d")
    except ValueError:
        return date_str


def _flat_events_to_markdown(events: list) -> str:
    """Format a flat list of event dicts as clean, readable Markdown."""
    if not events:
        return "_No events found._"
    blocks = []
    for i, event in enumerate(events, 1):
        name = event.get("name", "—")
        venue = event.get("venue", {})
        venue_name = venue.get("name", "—")
        date = event.get("date", "—")
        time = event.get("time", "")
        address = venue.get("address", "") or ""
        city = venue.get("city", "") or ""
        state = venue.get("state", "") or ""
        location = ", ".join(filter(None, [address, city, state]))
        date_display = _format_date(date)
        time_display = f" at {time}" if time else ""
        block = [
            f"### {i}. {name}",
            "",
            f"**Venue:** {venue_name}  ",
            f"**When:** {date_display}{time_display}  ",
        ]
        if location:
            block.append(f"**Where:** {location}  ")
        block.append("")
        blocks.append("\n".join(block))
    return "\n---\n\n".join(blocks).strip()


def _parse_interests(text: str) -> list:
    """Extract sports, music, movies from user text (comma/and/or)."""
    text = (text or "").lower()
    found = []
    if re.search(r"\bsports?\b", text):
        found.append("sports")
    if re.search(r"\bmusic\b", text):
        found.append("music")
    if re.search(r"\bmovies?\b|\bfilm(s)?\b", text):
        found.append("movies")
    return found if found else ["music", "sports", "movies"]


def _content_to_text(content) -> str:
    """Extract plain text from Gradio content (string or list of blocks like [{"text": "...", "type": "text"}])."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and "text" in block:
                parts.append(str(block["text"]).strip())
            else:
                parts.append(str(block).strip())
        return " ".join(parts).strip()
    return str(content).strip()


def _get_user_text(message) -> str:
    """Get plain text from user message (string or Gradio message dict)."""
    if message is None:
        return ""
    if isinstance(message, str):
        return message.strip()
    if isinstance(message, dict) and "content" in message:
        return _content_to_text(message["content"])
    return _content_to_text(message)


def chat(message, history):
    """Two-step: 1) city -> ask interests, 2) interests -> top 10 events."""
    text = _get_user_text(message)
    if not text:
        return "Please enter a city name."

    user_msgs = []
    if history:
        for h in history:
            if isinstance(h, dict) and h.get("role") == "user":
                user_msgs.append(_content_to_text(h.get("content")))

    if len(user_msgs) == 0:
        # First message = city
        city = get_city(text)
        if not city:
            return "Could not understand the city name. Please try again."
        return INTERESTS_PROMPT.format(city=city)

    # Second message = interests
    city = get_city(user_msgs[0])
    if not city:
        city = user_msgs[0]
    interests = _parse_interests(text)
    try:
        events = get_events_by_interests(city, interests, max_events=TOP_N)
    except Exception as e:
        return f"Could not load events: {e}"

    if not events:
        return f"## Events in {city}\n\n_No events found for your interests._"

    md = f"## Top {TOP_N} events in {city}\n\n" + _flat_events_to_markdown(events)
    return md


if __name__ == "__main__":
    with gr.Blocks() as demo:
        gr.Markdown("# EventAIde")
        chatbot = gr.Chatbot(
            value=[{"role": "assistant", "content": WELCOME}],
            height=400,
        )
        msg = gr.Textbox(placeholder="Type a city name, then your interests (e.g. music, sports)...", label="Message", show_label=False)
        clear = gr.Button("Clear")

        def respond(message, history):
            if not (message and str(message).strip()):
                return history, ""
            reply = chat(message, history)
            new_history = list(history) if history else [{"role": "assistant", "content": WELCOME}]
            new_history.append({"role": "user", "content": message})
            new_history.append({"role": "assistant", "content": reply})
            return new_history, ""

        def clear_chat():
            return [{"role": "assistant", "content": WELCOME}], ""

        msg.submit(respond, [msg, chatbot], [chatbot, msg])
        clear.click(clear_chat, None, [chatbot, msg])
    demo.launch()
