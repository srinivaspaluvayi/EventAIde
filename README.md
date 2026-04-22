# Multi-Agent AI Travel Planner

Production-ready, portfolio-quality travel planner built with:
- Python
- Agno (agent orchestration)
- GPT-4o-mini (small model)
- Streamlit UI

The app takes natural language travel preferences and produces:
- structured profile extraction
- destination research insights
- day-by-day itinerary (morning/afternoon/evening)
- logistics recommendations
- budget summary with chart
- downloadable `travel_plan.html`

## Architecture (5-Agent Pipeline)

1. `PreferenceCollectorAgent`
2. `DestinationResearchAgent`
3. `ItineraryPlannerAgent`
4. `LogisticsAgent`
5. `SummaryGeneratorAgent`

Pipeline orchestration lives in `src/travel_planner/orchestration/pipeline.py`.

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

### 4) Run the Streamlit app

```bash
streamlit run app.py
```

### 5) Run smoke tests

```bash
PYTHONPATH=src pytest -q
```

## Example Inputs

- “Plan a 5-day Tokyo trip in October, budget $1800, food + anime + photography, solo traveler.”
- “I need a 7-day Paris family trip in June, moderate budget, 2 adults + 2 kids, museums and parks.”
- “Backpacking in Bangkok for 4 days under $500, cheap transport, street food and nightlife.”

## Project Structure

- `app.py` — Streamlit app entrypoint
- `src/travel_planner/agents/` — all 5 agent implementations
- `src/travel_planner/orchestration/pipeline.py` — execution flow across agents
- `src/travel_planner/models/schemas.py` — strict Pydantic schemas
- `src/travel_planner/tools/search_tool.py` — free destination web research
- `src/travel_planner/utils/html_renderer.py` — HTML report generation
- `src/travel_planner/ui/charts.py` — matplotlib budget chart helper

## Production Notes

- Typed schemas at every boundary
- Fail-safe JSON parsing and fallback handling
- Small-model prompt design to control token cost
- Session-level logging for debugging and demos
- Legacy event-discovery code was removed to keep the repository clean and focused on this product.

## Troubleshooting

- If model calls fail, verify `OPENAI_API_KEY`.
- If research results are thin, increase `MAX_SEARCH_RESULTS`.
- If Streamlit does not start, ensure your venv is active and dependencies installed.
