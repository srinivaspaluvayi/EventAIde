"""
EventAIde MCP server: retrieves all event data from Ticketmaster and exposes it via tools.
Tools: get_all_events, get_music_events, get_sports_events, get_concerts.
Uses MCP SDK 1.26 decorator API (no ServerRequestContext).
"""
import json
import os
import re
import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from eventaide_mcp.ticketmaster import (
    get_all_events as tm_get_all_events,
    get_concerts as tm_get_concerts,
    get_music_events as tm_get_music_events,
    get_sports_events as tm_get_sports_events,
)

# Defaults (Rolla, MO; overridable via env)
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "Rolla")
DEFAULT_STATE_CODE = os.getenv("DEFAULT_STATE_CODE", "MO")


def _norm_args(arguments: dict | None) -> dict:
    args = dict(arguments or {})
    args.setdefault("city", DEFAULT_CITY)
    args.setdefault("stateCode", DEFAULT_STATE_CODE)
    return args


def _validate_dates(args: dict) -> None:
    for key in ("startDate", "endDate"):
        val = args.get(key)
        if val and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
            raise ValueError(f"Invalid {key}: {val} (expected YYYY-MM-DD)")


ALL_EVENTS_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string", "description": "City name (required)."},
        "stateCode": {"type": "string", "description": "US state code, e.g. MO."},
    },
}

BASE_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {"type": "string", "description": "City name (defaults via env)."},
        "stateCode": {"type": "string", "description": "US state code, e.g. MO."},
        "countryCode": {"type": "string", "default": "US"},
        "startDate": {"type": "string", "description": "YYYY-MM-DD"},
        "endDate": {"type": "string", "description": "YYYY-MM-DD"},
        "keyword": {"type": "string"},
        "format": {"type": "string", "enum": ["json", "text"], "default": "json"},
    },
}

# Create server and register handlers with decorator API (MCP SDK 1.26)
server = Server("eventaide-mcp")


@server.list_tools()
async def handle_list_tools() -> types.ListToolsResult:
    return types.ListToolsResult(
        tools=[
            types.Tool(
                name="get_all_events",
                description="Get all events in a city, grouped by segment and genre. Use this for a full event list.",
                inputSchema=ALL_EVENTS_SCHEMA,
            ),
            types.Tool(
                name="get_music_events",
                description="Find music events in a city/date range (classificationName=Music).",
                inputSchema=BASE_SCHEMA,
            ),
            types.Tool(
                name="get_sports_events",
                description="Find sports events in a city/date range (classificationName=Sports).",
                inputSchema=BASE_SCHEMA,
            ),
            types.Tool(
                name="get_concerts",
                description="Find concerts (music) in a city/date range; defaults keyword to 'concert'.",
                inputSchema=BASE_SCHEMA,
            ),
        ]
    )


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[types.TextContent] | types.CallToolResult:
    args = _norm_args(arguments)
    _validate_dates(args)

    if not args.get("city"):
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Error: Missing required 'city' (or set DEFAULT_CITY).")],
            isError=True,
        )

    city = args.get("city")
    state_code = args.get("stateCode")
    keyword = args.get("keyword")
    start_date = args.get("startDate")
    end_date = args.get("endDate")

    def _run_sync():
        if name == "get_all_events":
            return tm_get_all_events(city, state_code)
        if name == "get_music_events":
            return tm_get_music_events(city, state_code, keyword, start_date, end_date)
        if name == "get_sports_events":
            return tm_get_sports_events(city, state_code, keyword, start_date, end_date)
        if name == "get_concerts":
            return tm_get_concerts(city, state_code, keyword, start_date, end_date)
        raise ValueError(f"Unknown tool: {name}")

    try:
        result = await anyio.to_thread.run_sync(_run_sync)
        text = json.dumps(result, indent=2)
        return [types.TextContent(type="text", text=text)]
    except Exception as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Error: {e}")],
            isError=True,
        )


def main() -> int:
    async def run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(read_stream, write_stream, server.create_initialization_options())

    anyio.run(run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
