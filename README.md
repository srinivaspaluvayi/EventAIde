# EventAIde (Event + AI + Aide)

EventAIde is a chatbot that helps you discover events in any city. Enter a city, pick your interests (sports, music, movies), and get the top 10 events in a clean chat UI.

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/srinivaspaluvayi/EventAIde.git
cd EventAIde
```

### 2. Install dependencies

This project uses **Conda** for environment management.

```bash
conda env create -f environment.yaml
conda activate eventaide
```

If you use pip, install the dependencies listed in `environment.yaml` manually.

### 3. Environment variables

Create a `.env` file in the project root:

```
TICKETMASTER_API_KEY=your_api_key_here
```

Get a free API key from [Ticketmaster Developer](https://developer.ticketmaster.com/).

### 4. Run the app

From the project root (with the `eventaide` env active):

```bash
python app.py
```

Open the URL shown (e.g. http://127.0.0.1:7860). **Flow:**

1. The assistant greets you and asks for a **city** (e.g. New York, St Louis).
2. You enter a city; spelling is corrected via Ollama if needed.
3. The assistant asks for your **interests**: sports, music, and/or movies.
4. You reply (e.g. "music and sports"); you get the **top 10 events** in Markdown.

**Requirements:**

- **Ollama** running with a model (e.g. `llama3.2:latest`) for city name correction. Install from [ollama.ai](https://ollama.ai).
- **Ticketmaster API key** in `.env` (see step 3).

## Optional: MCP server

The **EventAIde MCP server** exposes Ticketmaster as tools for Cursor or other MCP clients. The Gradio app does **not** use this server; it calls `eventaide_mcp.ticketmaster` directly.

To run the MCP server (e.g. for Cursor):

1. From the project root: `python -m eventaide_mcp.server`
2. Add it to Cursor’s MCP config (see `mcp-config.example.json`) and set `TICKETMASTER_API_KEY` in `env`.

**Tools:** `get_all_events`, `get_music_events`, `get_sports_events`, `get_concerts`.

## Project layout

- **`app.py`** — Gradio chat UI (city → interests → top 10 events).
- **`city_corrections.py`** — City name spelling correction (Ollama).
- **`eventaide_mcp/ticketmaster.py`** — Ticketmaster Discovery API (used by the app and by the MCP server).
- **`eventaide_mcp/server.py`** — MCP server entrypoint.
