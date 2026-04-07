"""
Tool implementations for the Trip Planner Agent.
Each tool is a standalone function that can be called by the agent loop.
"""

import json
import requests
from datetime import datetime, timedelta

try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


# ─────────────────────────────────────────────────────────────────
# TOOL 1: Web Search
# ─────────────────────────────────────────────────────────────────


def search_web(query: str, max_results: int = 5) -> dict:
    import concurrent.futures

    def _search():
        with DDGS() as ddgs:
            return list(ddgs.text(query, max_results=max_results))

    try:
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(_search)
            try:
                results = future.result(timeout=6)
            except concurrent.futures.TimeoutError:
                return {"success": False, "error": "Search timed out", "results": []}
        return {
            "success": True,
            "query": query,
            "results": [
                {
                    "title": r.get("title", ""),
                    "body": r.get("body", ""),
                    "href": r.get("href", ""),
                }
                for r in results
            ],
        }
    except Exception as e:
        return {"success": False, "error": str(e), "results": []}


# ─────────────────────────────────────────────────────────────────
# TOOL 2: Weather Forecast
# ─────────────────────────────────────────────────────────────────


def get_weather_forecast(city: str, start_date: str, end_date: str) -> dict:
    """
    Get weather forecast for a city and date range.
    Uses Open-Meteo API (free, no API key required).
    Dates should be in YYYY-MM-DD format.
    """
    try:
        # Step 1: Geocode the city
        geo_url = "https://geocoding-api.open-meteo.com/v1/search"
        geo_resp = requests.get(
            geo_url,
            params={"name": city, "count": 1, "language": "en", "format": "json"},
            timeout=10,
        )
        geo_data = geo_resp.json()

        if not geo_data.get("results"):
            return {"success": False, "error": f"Could not find location: {city}"}

        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        timezone = loc.get("timezone", "auto")

        # Step 2: Fetch weather
        weather_url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
            "timezone": timezone,
            "start_date": start_date,
            "end_date": end_date,
            "temperature_unit": "fahrenheit",
        }
        w_resp = requests.get(weather_url, params=params, timeout=10)
        w_data = w_resp.json()

        daily = w_data.get("daily", {})
        dates = daily.get("time", [])
        max_temps = daily.get("temperature_2m_max", [])
        min_temps = daily.get("temperature_2m_min", [])
        precip = daily.get("precipitation_sum", [])
        codes = daily.get("weathercode", [])

        # WMO weather code descriptions
        wmo_descriptions = {
            0: "Clear sky",
            1: "Mainly clear",
            2: "Partly cloudy",
            3: "Overcast",
            45: "Foggy",
            48: "Icy fog",
            51: "Light drizzle",
            53: "Moderate drizzle",
            55: "Dense drizzle",
            61: "Slight rain",
            63: "Moderate rain",
            65: "Heavy rain",
            71: "Slight snow",
            73: "Moderate snow",
            75: "Heavy snow",
            77: "Snow grains",
            80: "Slight showers",
            81: "Moderate showers",
            82: "Violent showers",
            85: "Slight snow showers",
            86: "Heavy snow showers",
            95: "Thunderstorm",
            96: "Thunderstorm with hail",
            99: "Thunderstorm with heavy hail",
        }

        forecast = []
        for i, date in enumerate(dates):
            forecast.append(
                {
                    "date": date,
                    "high_f": (
                        round(max_temps[i], 1)
                        if i < len(max_temps) and max_temps[i] is not None
                        else "N/A"
                    ),
                    "low_f": (
                        round(min_temps[i], 1)
                        if i < len(min_temps) and min_temps[i] is not None
                        else "N/A"
                    ),
                    "precipitation_mm": (
                        round(precip[i], 1)
                        if i < len(precip) and precip[i] is not None
                        else 0
                    ),
                    "condition": wmo_descriptions.get(
                        codes[i] if i < len(codes) else 0, "Unknown"
                    ),
                }
            )

        return {
            "success": True,
            "city": loc["name"],
            "country": loc.get("country", ""),
            "forecast": forecast,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────
# TOOL 3: Place Details Lookup
# ─────────────────────────────────────────────────────────────────


def get_place_details(place_name: str, city: str) -> dict:
    """
    Get details about a specific place (attraction, restaurant, hotel).
    Uses Nominatim for geocoding + DuckDuckGo for additional info.
    """
    try:
        # Nominatim lookup
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "q": f"{place_name}, {city}",
            "format": "json",
            "limit": 1,
            "addressdetails": 1,
            "extratags": 1,
        }
        headers = {"User-Agent": "TripPlannerAgent/1.0"}
        resp = requests.get(nominatim_url, params=params, headers=headers, timeout=10)
        data = resp.json()

        place_info = {}
        if data:
            item = data[0]
            place_info = {
                "name": place_name,
                "city": city,
                "type": item.get("type", ""),
                "category": item.get("class", ""),
                "lat": item.get("lat"),
                "lon": item.get("lon"),
                "address": item.get("display_name", ""),
                "extra": item.get("extratags", {}),
            }

        # Supplement with a web search for hours, admission, tips
        search_query = (
            f"{place_name} {city} opening hours admission price tips visitors"
        )
        with DDGS() as ddgs:
            search_results = list(ddgs.text(search_query, max_results=3))

        snippets = [r.get("body", "") for r in search_results]

        return {
            "success": True,
            "place": place_info if place_info else {"name": place_name, "city": city},
            "info_snippets": snippets,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────
# TOOL 4: Cost Estimator
# ─────────────────────────────────────────────────────────────────


def estimate_travel_costs(
    destination: str,
    num_days: int,
    accommodation_type: str = "mid-range",
    travel_style: str = "standard",
) -> dict:
    """
    Estimate realistic daily travel costs for a destination.
    Uses a heuristic cost database supplemented by web search.
    accommodation_type: "budget", "mid-range", "luxury"
    travel_style: "backpacker", "standard", "comfort", "luxury"
    """

    # Baseline city cost tiers (USD/day for a single traveler, mid-range)
    # These are rough estimates; agent should adjust based on search results
    city_cost_tiers = {
        # Expensive cities
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
        "sydney": {
            "accommodation": {"budget": 60, "mid-range": 180, "luxury": 500},
            "food": {"budget": 20, "mid-range": 55, "luxury": 130},
            "activities": 30,
            "transport": 15,
        },
        "amsterdam": {
            "accommodation": {"budget": 60, "mid-range": 160, "luxury": 450},
            "food": {"budget": 20, "mid-range": 55, "luxury": 130},
            "activities": 25,
            "transport": 10,
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
        "berlin": {
            "accommodation": {"budget": 40, "mid-range": 120, "luxury": 350},
            "food": {"budget": 15, "mid-range": 40, "luxury": 100},
            "activities": 20,
            "transport": 10,
        },
        # Budget-friendly
        "bangkok": {
            "accommodation": {"budget": 15, "mid-range": 60, "luxury": 200},
            "food": {"budget": 8, "mid-range": 25, "luxury": 70},
            "activities": 15,
            "transport": 8,
        },
        "bali": {
            "accommodation": {"budget": 20, "mid-range": 70, "luxury": 250},
            "food": {"budget": 10, "mid-range": 25, "luxury": 70},
            "activities": 20,
            "transport": 10,
        },
        "lisbon": {
            "accommodation": {"budget": 35, "mid-range": 110, "luxury": 350},
            "food": {"budget": 15, "mid-range": 40, "luxury": 100},
            "activities": 15,
            "transport": 8,
        },
        "prague": {
            "accommodation": {"budget": 30, "mid-range": 100, "luxury": 300},
            "food": {"budget": 12, "mid-range": 35, "luxury": 90},
            "activities": 15,
            "transport": 5,
        },
        "mexico city": {
            "accommodation": {"budget": 25, "mid-range": 80, "luxury": 250},
            "food": {"budget": 12, "mid-range": 30, "luxury": 80},
            "activities": 15,
            "transport": 8,
        },
    }

    dest_lower = destination.lower()
    costs = None
    for city, data in city_cost_tiers.items():
        if city in dest_lower or dest_lower in city:
            costs = data
            break

    # Default to mid-tier estimate if city not found
    if not costs:
        costs = {
            "accommodation": {"budget": 50, "mid-range": 150, "luxury": 400},
            "food": {"budget": 20, "mid-range": 50, "luxury": 130},
            "activities": 25,
            "transport": 12,
        }

    acc_type = (
        accommodation_type
        if accommodation_type in ["budget", "mid-range", "luxury"]
        else "mid-range"
    )
    style_multipliers = {
        "backpacker": 0.7,
        "standard": 1.0,
        "comfort": 1.4,
        "luxury": 2.0,
    }
    multiplier = style_multipliers.get(travel_style, 1.0)

    daily_accommodation = costs["accommodation"][acc_type]
    daily_food = costs["food"][acc_type] * multiplier
    daily_activities = costs["activities"] * multiplier
    daily_transport = costs["transport"]

    daily_total = daily_accommodation + daily_food + daily_activities + daily_transport
    trip_total = daily_total * num_days

    return {
        "success": True,
        "destination": destination,
        "num_days": num_days,
        "accommodation_type": acc_type,
        "travel_style": travel_style,
        "daily_breakdown": {
            "accommodation": round(daily_accommodation, 2),
            "food": round(daily_food, 2),
            "activities": round(daily_activities, 2),
            "local_transport": round(daily_transport, 2),
            "total": round(daily_total, 2),
        },
        "trip_total_estimate": round(trip_total, 2),
        "note": "These are estimates. Actual costs vary based on season, specific choices, and travel style.",
    }


# ─────────────────────────────────────────────────────────────────
# Tool Registry & Dispatcher
# ─────────────────────────────────────────────────────────────────

TOOL_FUNCTIONS = {
    "search_web": search_web,
    "get_weather_forecast": get_weather_forecast,
    "get_place_details": get_place_details,
    "estimate_travel_costs": estimate_travel_costs,
}

TOOL_DEFINITIONS = [
    {
        "name": "search_web",
        "description": "Search the web for travel information, attractions, restaurants, hotels, tips, and travel guides. Use this to find what to do, see, and eat in a destination.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query, e.g. 'best restaurants in Tokyo for food lovers' or 'top attractions in Paris itinerary'",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Number of results to return (default 5, max 8)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "get_weather_forecast",
        "description": "Get the weather forecast for a city over a date range. Use this to inform packing recommendations and outdoor activity planning.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "City name, e.g. 'Paris', 'Tokyo', 'New York'",
                },
                "start_date": {
                    "type": "string",
                    "description": "Start date in YYYY-MM-DD format",
                },
                "end_date": {
                    "type": "string",
                    "description": "End date in YYYY-MM-DD format",
                },
            },
            "required": ["city", "start_date", "end_date"],
        },
    },
    {
        "name": "get_place_details",
        "description": "Get details about a specific attraction, restaurant, museum, or landmark including location info and visitor tips.",
        "input_schema": {
            "type": "object",
            "properties": {
                "place_name": {
                    "type": "string",
                    "description": "Name of the place, e.g. 'Eiffel Tower', 'Tsukiji Market', 'The Colosseum'",
                },
                "city": {
                    "type": "string",
                    "description": "The city where the place is located",
                },
            },
            "required": ["place_name", "city"],
        },
    },
    {
        "name": "estimate_travel_costs",
        "description": "Estimate realistic daily and total travel costs for a destination to ensure the itinerary fits within the user's budget.",
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "Destination city or country",
                },
                "num_days": {
                    "type": "integer",
                    "description": "Number of days of the trip",
                },
                "accommodation_type": {
                    "type": "string",
                    "enum": ["budget", "mid-range", "luxury"],
                    "description": "Type of accommodation. Infer from budget: budget hostels/guesthouses, mid-range hotels, luxury resorts.",
                },
                "travel_style": {
                    "type": "string",
                    "enum": ["backpacker", "standard", "comfort", "luxury"],
                    "description": "Overall travel style/spending level",
                },
            },
            "required": ["destination", "num_days"],
        },
    },
]


def execute_tool(tool_name: str, tool_input: dict) -> dict:
    """Dispatch a tool call to the appropriate function."""
    if tool_name not in TOOL_FUNCTIONS:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    try:
        return TOOL_FUNCTIONS[tool_name](**tool_input)
    except Exception as e:
        return {"success": False, "error": f"Tool execution error: {str(e)}"}
