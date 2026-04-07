# Bon Voyage 🌍 — AI Trip Planner Agent

An LLM-based travel planning agent that creates detailed, day-by-day trip itineraries using live web search, real weather forecasts, and budget validation.

Built from scratch — no LangChain, CrewAI, or agent frameworks. The agent loop is implemented directly.

---

## Features

- **Custom agent loop** — ReAct-style planning loop with tool-calling, implemented without any agent framework
- **4 tools** — web search, weather forecast, place details, cost estimator
- **Streaming UI** — real-time activity log shows what the agent is doing as it works
- **Evaluation framework** — constraint satisfaction scoring + LLM-as-judge rubric across 10 test cases

---

## Architecture

```
User Request
     │
     ▼
┌─────────────────────────────────────────────┐
│              TripPlannerAgent               │
│                                             │
│  1. Send request + tool definitions         │
│     to Claude (claude-sonnet-4-6)           │
│                                             │
│  2. If stop_reason == "tool_use":           │
│       Execute tools → append results        │
│       Loop back to step 1                   │
│                                             │
│  3. If stop_reason == "end_turn":           │
│       Return final itinerary                │
└─────────────────────────────────────────────┘
         │
    Tools Used:
    ├── search_web()           → DuckDuckGo (free, no API key)
    ├── get_weather_forecast() → Open-Meteo API (free, no API key)
    ├── get_place_details()    → Nominatim + DuckDuckGo
    └── estimate_travel_costs()→ Custom heuristic database
```

### Files

```
trip-planner-agent/
├── agent.py          # Agent loop (planning + tool dispatch)
├── tools.py          # All 4 tool implementations + definitions
├── app.py            # Flask server (REST + SSE streaming)
├── static/
│   └── index.html    # Frontend UI (single file, no build step)
├── eval/
│   ├── test_cases.json   # 10 structured test cases
│   ├── evaluator.py      # Constraint + LLM-as-judge eval
│   └── results/          # Saved evaluation outputs
├── requirements.txt
└── .env.example
```

---

## Setup

### 1. Clone & install

```bash
git clone <repo-url>
cd trip-planner-agent
pip install -r requirements.txt
```

### 2. Set your API key

```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

> **Note:** Only `ANTHROPIC_API_KEY` is required. Web search (DuckDuckGo) and weather (Open-Meteo) are both free and need no keys.

### 3. Run the web app

```bash
python app.py
```

Open [http://localhost:5001](http://localhost:5001) in your browser.

---

## Tools

| Tool | Source | API Key? | Purpose |
|------|--------|----------|---------|
| `search_web` | DuckDuckGo | ❌ Free | Find attractions, restaurants, hotels, tips |
| `get_weather_forecast` | Open-Meteo | ❌ Free | Real forecast for trip dates |
| `get_place_details` | Nominatim + DDG | ❌ Free | Hours, admission, visitor info |
| `estimate_travel_costs` | Custom database | ❌ None | Budget validation |

---

## Evaluation

The evaluation runs the agent on 10 predefined test cases and scores each output on two dimensions:

### A) Constraint Satisfaction (objective, 0–1)
Programmatic checks on the itinerary text:
- Destination mentioned
- Correct number of days
- Budget addressed
- Interests covered
- Day-by-day structure present
- Weather mentioned (if dates provided)
- Transportation mentioned
- Travel party considered

### B) LLM-as-Judge (subjective, 1–5 per dimension)
Claude scores each itinerary on:
- **Coherence** — logical flow, realistic timing
- **Specificity** — real place names, not vague suggestions
- **Budget Fit** — realistic for stated budget
- **Interest Match** — genuinely caters to user interests
- **Practicality** — actionable advice, booking tips
- **Completeness** — covers all days requested

### Running the eval

```bash
# Run all 10 test cases
python eval/evaluator.py

# Run specific test cases (faster for testing)
python eval/evaluator.py --cases 1,2,3

# Save results to a specific file
python eval/evaluator.py --out eval/results/my_run.json
```

Results are saved to `eval/results/` as JSON files containing full itinerary text, scores, and a summary.

---

## Example Usage

**Input:**
> "5 days in Tokyo starting 2025-04-01, $200/day, first-time visitor, love food and pop culture"

**Agent actions:**
1. `search_web("Tokyo 5 day itinerary first time visitor food pop culture")`
2. `get_weather_forecast("Tokyo", "2025-04-01", "2025-04-05")`
3. `get_place_details("Tsukiji Outer Market", "Tokyo")`
4. `get_place_details("Shibuya Crossing", "Tokyo")`
5. `estimate_travel_costs("Tokyo", 5, "mid-range", "standard")`
6. → Returns full day-by-day itinerary

**Output:** Structured 5-day itinerary with morning/afternoon/evening activities, weather summary, packing tips, budget breakdown, and pro tips.

---

## Design Decisions

**Why no framework?** The assignment requires implementing the agent loop directly. The loop in `agent.py` is ~60 lines and handles all the tool-calling logic — it's actually simpler to read than equivalent LangChain code.

**Why DuckDuckGo?** Free, no API key, good enough for travel info. SerpAPI or Tavily would give cleaner results but add a paid dependency.

**Why Open-Meteo?** Completely free weather API with no key required. 16-day forecast horizon covers most near-term trips.

**Why two eval dimensions?** Constraint satisfaction catches objective failures (wrong day count, missing budget info). LLM-as-judge catches quality failures that are hard to check programmatically (vague suggestions, poor coherence).

---

## Requirements

- Python 3.10+
- Anthropic API key (Claude Sonnet)
- Internet connection (for DuckDuckGo + Open-Meteo)
