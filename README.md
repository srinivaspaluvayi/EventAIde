# Multi-Agent AI Travel Planner

Production-ready, portfolio-quality travel planner built with:
- Python
- Agno (agent orchestration)
- GPT-4o-mini (small model)
- FastAPI backend + Streamlit UI

The app takes natural language travel preferences and produces:
- structured profile extraction
- destination research insights
- day-by-day itinerary (morning/afternoon/evening)
- logistics recommendations
- budget summary with chart
- downloadable `travel_plan.html`

## Architecture (Production Split)

Backend (FastAPI):
- API layer: `src/travel_planner/backend/app.py`
- Service layer: `src/travel_planner/backend/service.py`
- Contracts: `src/travel_planner/backend/schemas.py`
- Agent orchestration: `src/travel_planner/orchestration/pipeline.py`

Agent team:
1. `PreferenceCollectorAgent`
2. `DestinationResearchAgent`
3. `FlightSearchAgent`
4. `HotelSearchAgent`
5. `DiningAgent`
6. `BudgetOptimizerAgent`
7. `ItineraryPlannerAgent`
8. `LogisticsAgent`
9. `SummaryGeneratorAgent`

## Setup

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
```

### 2) Install dependencies

```bash
pip install -r requirements.txt
```

### 3) Configure environment variables

Copy `.env.example` to `.env` and fill values:

```bash
cp .env.example .env
```

Required:
- `OPENAI_API_KEY`

Optional:
- `OPENAI_MODEL=gpt-4o-mini`
- `MAX_SEARCH_RESULTS=6`
- `TRIPFORGE_BACKEND_URL=http://127.0.0.1:8000`
- `SERPAPI_API_KEY` (for real hotel search integration)
- `FOURSQUARE_API_KEY` (for real dining/places integration)

### 4) Run the backend API

```bash
PYTHONPATH=src uvicorn travel_planner.backend.app:app --host 0.0.0.0 --port 8000
```

### 5) Run the Streamlit app

```bash
streamlit run app.py
```

### 6) Run smoke tests

```bash
PYTHONPATH=src pytest -q
```

## Example Inputs

- “Plan a 5-day Tokyo trip in October, budget $1800, food + anime + photography, solo traveler.”
- “I need a 7-day Paris family trip in June, moderate budget, 2 adults + 2 kids, museums and parks.”
- “Backpacking in Bangkok for 4 days under $500, cheap transport, street food and nightlife.”

## Project Structure

- `app.py` — Streamlit frontend (calls backend API)
- `src/travel_planner/backend/` — FastAPI app, service layer, and API contracts
- `src/travel_planner/agents/` — specialized multi-agent implementations
- `src/travel_planner/agents/team_orchestrator.py` — team coordination across specialist agents
- `src/travel_planner/orchestration/pipeline.py` — execution flow across agents
- `src/travel_planner/models/schemas.py` — strict Pydantic schemas
- `src/travel_planner/tools/search_tool.py` — free destination web research
- `src/travel_planner/utils/html_renderer.py` — HTML report generation
- `src/travel_planner/ui/charts.py` — matplotlib budget chart helper

## Production Notes

- Typed schemas at every boundary
- Explicit backend/frontend boundary for deployability and API reuse
- Fail-safe JSON parsing and fallback handling
- Small-model prompt design to control token cost
- Session-level logging for debugging and demos
- Legacy event-discovery code was removed to keep the repository clean and focused on this product.

## Troubleshooting

- If model calls fail, verify `OPENAI_API_KEY`.
- If frontend cannot reach backend, verify `TRIPFORGE_BACKEND_URL` and that FastAPI is running on port `8000`.
- If hotel or dining results look generic, add `SERPAPI_API_KEY` and `FOURSQUARE_API_KEY` to enable live provider data.
- If research results are thin, increase `MAX_SEARCH_RESULTS`.
- If Streamlit does not start, ensure your venv is active and dependencies installed.
