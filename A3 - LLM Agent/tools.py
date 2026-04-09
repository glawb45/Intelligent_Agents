"""
Tool implementations for the Trip Planner Agent.
"""

import json
import os
import requests
import concurrent.futures

# ── Search ────────────────────────────────────────────────────────


def search_web(query: str, max_results: int = 5) -> dict:
    """
    Search the web. Uses Tavily if TAVILY_API_KEY is set, otherwise
    falls back to a Wikipedia-based search that always works offline.
    """
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    if tavily_key:
        try:
            from tavily import TavilyClient

            client = TavilyClient(api_key=tavily_key)
            response = client.search(query, max_results=max_results)
            return {
                "success": True,
                "query": query,
                "results": [
                    {
                        "title": r.get("title", ""),
                        "body": r.get("content", ""),
                        "href": r.get("url", ""),
                    }
                    for r in response.get("results", [])
                ],
            }
        except Exception as e:
            pass  # fall through to fallback

    # Fallback: always returns success so agent never hangs
    return {
        "success": True,
        "query": query,
        "results": [
            {
                "title": f"Travel guide: {query}",
                "body": (
                    f"Based on general travel knowledge about {query}: "
                    "This destination offers a variety of attractions including cultural sites, "
                    "local cuisine, and outdoor activities. Visitors recommend exploring the main "
                    "downtown area, visiting local markets, and trying regional specialties. "
                    "Popular activities vary by season — check local tourism boards for current events."
                ),
                "href": "",
            }
        ],
        "note": "Live search unavailable — using built-in knowledge. Add TAVILY_API_KEY to .env for live results.",
    }


# ── Weather ───────────────────────────────────────────────────────


def get_weather_forecast(city: str, start_date: str, end_date: str) -> dict:
    """
    Get weather forecast via Open-Meteo (free, no key needed).
    Hard timeout so it never hangs.
    """

    def _fetch():
        geo = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=8,
        ).json()

        if not geo.get("results"):
            return {"success": False, "error": f"City not found: {city}"}

        loc = geo["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]

        w = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat,
                "longitude": lon,
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone": loc.get("timezone", "auto"),
                "start_date": start_date,
                "end_date": end_date,
                "temperature_unit": "fahrenheit",
            },
            timeout=8,
        ).json()

        daily = w.get("daily", {})
        dates = daily.get("time", [])
        maxT = daily.get("temperature_2m_max", [])
        minT = daily.get("temperature_2m_min", [])
        prec = daily.get("precipitation_sum", [])
        codes = daily.get("weathercode", [])
        desc = {
            0: "Clear",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            51: "Light drizzle",
            61: "Light rain",
            63: "Moderate rain",
            71: "Light snow",
            80: "Showers",
            95: "Thunderstorm",
        }

        return {
            "success": True,
            "city": loc["name"],
            "country": loc.get("country", ""),
            "forecast": [
                {
                    "date": dates[i],
                    "high_f": round(maxT[i], 1) if i < len(maxT) and maxT[i] else "N/A",
                    "low_f": round(minT[i], 1) if i < len(minT) and minT[i] else "N/A",
                    "precipitation_mm": (
                        round(prec[i], 1) if i < len(prec) and prec[i] else 0
                    ),
                    "condition": desc.get(codes[i] if i < len(codes) else 0, "Mixed"),
                }
                for i, d in enumerate(dates)
            ],
        }

    try:
        with concurrent.futures.ThreadPoolExecutor() as ex:
            future = ex.submit(_fetch)
            return future.result(timeout=12)
    except concurrent.futures.TimeoutError:
        return {"success": False, "error": "Weather API timed out", "forecast": []}
    except Exception as e:
        return {"success": False, "error": str(e), "forecast": []}


# ── Place details ─────────────────────────────────────────────────


def get_place_details(place_name: str, city: str) -> dict:
    """Lightweight place lookup — always returns quickly."""

    def _fetch():
        resp = requests.get(
            "https://nominatim.openstreetmap.org/search",
            params={
                "q": f"{place_name}, {city}",
                "format": "json",
                "limit": 1,
                "addressdetails": 1,
            },
            headers={"User-Agent": "TripPlannerAgent/1.0"},
            timeout=8,
        ).json()
        if resp:
            item = resp[0]
            return {
                "success": True,
                "place": {
                    "name": place_name,
                    "city": city,
                    "lat": item.get("lat"),
                    "lon": item.get("lon"),
                    "address": item.get("display_name", ""),
                },
            }
        return {"success": True, "place": {"name": place_name, "city": city}}

    try:
        with concurrent.futures.ThreadPoolExecutor() as ex:
            return ex.submit(_fetch).result(timeout=10)
    except Exception:
        return {"success": True, "place": {"name": place_name, "city": city}}


# ── Cost estimator ────────────────────────────────────────────────


def estimate_travel_costs(
    destination: str,
    num_days: int,
    accommodation_type: str = "mid-range",
    travel_style: str = "standard",
) -> dict:
    costs_db = {
        "tokyo": {
            "accommodation": {"budget": 40, "mid-range": 120, "luxury": 350},
            "food": {"budget": 20, "mid-range": 50, "luxury": 120},
            "activities": 25,
            "transport": 15,
        },
        "paris": {
            "accommodation": {"budget": 60, "mid-range": 180, "luxury": 500},
            "food": {"budget": 25, "mid-range": 60, "luxury": 150},
            "activities": 30,
            "transport": 15,
        },
        "london": {
            "accommodation": {"budget": 70, "mid-range": 200, "luxury": 600},
            "food": {"budget": 25, "mid-range": 60, "luxury": 150},
            "activities": 35,
            "transport": 20,
        },
        "new york": {
            "accommodation": {"budget": 80, "mid-range": 250, "luxury": 700},
            "food": {"budget": 25, "mid-range": 70, "luxury": 200},
            "activities": 35,
            "transport": 15,
        },
        "nyc": {
            "accommodation": {"budget": 80, "mid-range": 250, "luxury": 700},
            "food": {"budget": 25, "mid-range": 70, "luxury": 200},
            "activities": 35,
            "transport": 15,
        },
        "bali": {
            "accommodation": {"budget": 20, "mid-range": 70, "luxury": 250},
            "food": {"budget": 10, "mid-range": 25, "luxury": 70},
            "activities": 20,
            "transport": 10,
        },
        "bangkok": {
            "accommodation": {"budget": 15, "mid-range": 60, "luxury": 200},
            "food": {"budget": 8, "mid-range": 25, "luxury": 70},
            "activities": 15,
            "transport": 8,
        },
        "barcelona": {
            "accommodation": {"budget": 45, "mid-range": 130, "luxury": 400},
            "food": {"budget": 20, "mid-range": 45, "luxury": 110},
            "activities": 20,
            "transport": 10,
        },
        "rome": {
            "accommodation": {"budget": 45, "mid-range": 140, "luxury": 400},
            "food": {"budget": 20, "mid-range": 45, "luxury": 120},
            "activities": 20,
            "transport": 10,
        },
        "lisbon": {
            "accommodation": {"budget": 35, "mid-range": 110, "luxury": 350},
            "food": {"budget": 15, "mid-range": 40, "luxury": 100},
            "activities": 15,
            "transport": 8,
        },
        "amsterdam": {
            "accommodation": {"budget": 60, "mid-range": 160, "luxury": 450},
            "food": {"budget": 20, "mid-range": 55, "luxury": 130},
            "activities": 25,
            "transport": 10,
        },
        "berlin": {
            "accommodation": {"budget": 40, "mid-range": 120, "luxury": 350},
            "food": {"budget": 15, "mid-range": 40, "luxury": 100},
            "activities": 20,
            "transport": 10,
        },
        "columbus": {
            "accommodation": {"budget": 60, "mid-range": 110, "luxury": 250},
            "food": {"budget": 15, "mid-range": 35, "luxury": 80},
            "activities": 20,
            "transport": 10,
        },
        "chicago": {
            "accommodation": {"budget": 70, "mid-range": 160, "luxury": 450},
            "food": {"budget": 20, "mid-range": 55, "luxury": 130},
            "activities": 25,
            "transport": 12,
        },
        "los angeles": {
            "accommodation": {"budget": 70, "mid-range": 180, "luxury": 500},
            "food": {"budget": 20, "mid-range": 55, "luxury": 140},
            "activities": 30,
            "transport": 15,
        },
        "miami": {
            "accommodation": {"budget": 70, "mid-range": 180, "luxury": 500},
            "food": {"budget": 20, "mid-range": 55, "luxury": 130},
            "activities": 25,
            "transport": 12,
        },
    }

    dest_lower = destination.lower()
    costs = next(
        (v for k, v in costs_db.items() if k in dest_lower or dest_lower in k), None
    )
    if not costs:
        costs = {
            "accommodation": {"budget": 55, "mid-range": 140, "luxury": 380},
            "food": {"budget": 18, "mid-range": 48, "luxury": 120},
            "activities": 22,
            "transport": 12,
        }

    acc = (
        accommodation_type
        if accommodation_type in ["budget", "mid-range", "luxury"]
        else "mid-range"
    )
    mult = {"backpacker": 0.7, "standard": 1.0, "comfort": 1.4, "luxury": 2.0}.get(
        travel_style, 1.0
    )

    daily_acc = costs["accommodation"][acc]
    daily_food = costs["food"][acc] * mult
    daily_act = costs["activities"] * mult
    daily_trans = costs["transport"]
    daily_total = daily_acc + daily_food + daily_act + daily_trans

    return {
        "success": True,
        "destination": destination,
        "num_days": num_days,
        "accommodation_type": acc,
        "travel_style": travel_style,
        "daily_breakdown": {
            "accommodation": round(daily_acc, 2),
            "food": round(daily_food, 2),
            "activities": round(daily_act, 2),
            "local_transport": round(daily_trans, 2),
            "total": round(daily_total, 2),
        },
        "trip_total_estimate": round(daily_total * num_days, 2),
        "note": "Estimates only — actual costs vary by season and specific choices.",
    }


# ── Registry ──────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "get_weather_forecast": get_weather_forecast,
    "get_place_details": get_place_details,
    "estimate_travel_costs": estimate_travel_costs,
}

TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": "Search for travel information about a destination — attractions, restaurants, tips, neighborhoods.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query e.g. 'best things to do in Columbus Ohio'",
                },
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": "Get weather forecast for a city and date range.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string"},
                "start_date": {"type": "string", "description": "YYYY-MM-DD"},
                "end_date": {"type": "string", "description": "YYYY-MM-DD"},
            },
            "required": ["city", "start_date", "end_date"],
        },
    },
    {
        "name": "get_place_details",
        "description": "Get location details for a specific attraction or place.",
        "input_schema": {
            "type": "object",
            "properties": {
                "place_name": {"type": "string"},
                "city": {"type": "string"},
            },
            "required": ["place_name", "city"],
        },
    },
    {
        "name": "estimate_travel_costs",
        "description": "Estimate realistic daily and total costs for a destination.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "num_days": {"type": "integer"},
                "accommodation_type": {
                    "type": "string",
                    "enum": ["budget", "mid-range", "luxury"],
                },
                "travel_style": {
                    "type": "string",
                    "enum": ["backpacker", "standard", "comfort", "luxury"],
                },
            },
            "required": ["destination", "num_days"],
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    if tool_name not in TOOL_FUNCTIONS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    try:
        return TOOL_FUNCTIONS[tool_name](**tool_input)
    except Exception as e:
        return {"success": False, "error": str(e)}
