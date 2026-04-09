"""
Trip Planner Agent — core loop.
Supports OpenAI (default) and Anthropic backends.
Set LLM_PROVIDER=openai or anthropic in .env
"""

import json
import os
from typing import Callable, Optional
from tools import TOOL_DEFINITIONS, execute_tool

# Move this here so it loads in the main thread!
from openai import OpenAI

SYSTEM_PROMPT = """You are an expert travel planner. Create detailed, realistic day-by-day itineraries.

## Process
1. Call search_web to find attractions, food, and tips for the destination
2. Call get_weather_forecast if dates are given
3. Call get_place_details for 1-2 key attractions
4. Call estimate_travel_costs to validate the budget
5. Write the full itinerary

## Output Format
- **Trip Overview**: destination, dates, duration, budget
- **Weather**: what to expect, what to pack
- **Day-by-Day**: Morning / Afternoon / Evening for each day with specific place names
- **Budget Breakdown**: daily costs and trip total
- **Pro Tips**: 3-5 insider tips
- **Getting Around**: transport advice

## Rules
- Always call estimate_travel_costs
- Use real, specific place names
- Keep tool calls to 5 or fewer total to stay fast
- If search returns limited results, use your own knowledge — it's extensive
"""


def _openai_tool_defs():
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in TOOL_DEFINITIONS
    ]


class OpenAIBackend:
    def __init__(self, model="gpt-4o"):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.tool_defs = _openai_tool_defs()

    def run(
        self, user_message, on_tool_call=None, on_tool_result=None, max_iterations=10
    ):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        tool_call_log = []

        for iteration in range(max_iterations):
            print(f"[openai] Iteration {iteration+1}, messages={len(messages)}")
            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                tools=self.tool_defs,
                messages=messages,
                timeout=60,
            )

            choice = response.choices[0]
            msg = choice.message

            # Change this line! If you just append(msg), the OpenAI SDK will
            # crash when trying to validate an empty content field.
            messages.append(msg.model_dump(exclude_unset=True))

            print(
                f"[openai] finish_reason={choice.finish_reason}, tool_calls={bool(msg.tool_calls)}"
            )

            if choice.finish_reason == "stop" or not msg.tool_calls:
                return {
                    "itinerary": msg.content or "",
                    "tool_calls": tool_call_log,
                    "iterations": iteration + 1,
                    "error": None,
                }

            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_input = json.loads(tc.function.arguments)
                print(f"[openai] Calling tool: {tool_name}")

                if on_tool_call:
                    on_tool_call(tool_name, tool_input)

                result = execute_tool(tool_name, tool_input)
                print(
                    f"[openai] Tool done: {tool_name} success={result.get('success')}"
                )

                if on_tool_result:
                    on_tool_result(tool_name, result)

                tool_call_log.append(
                    {
                        "iteration": iteration + 1,
                        "tool": tool_name,
                        "input": tool_input,
                        "success": result.get("success", True),
                    }
                )
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": json.dumps(result),
                    }
                )

        return {
            "itinerary": "",
            "tool_calls": tool_call_log,
            "iterations": max_iterations,
            "error": "Max iterations reached",
        }


class GeminiBackend(OpenAIBackend):
    # 👇 Change the model string right here
    def __init__(self, model="gemini-2.5-flash"):
        from openai import OpenAI

        self.client = OpenAI(
            api_key=os.environ.get("GEMINI_API_KEY"),
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        self.model = model
        self.tool_defs = _openai_tool_defs()


class TripPlannerAgent:
    def __init__(self):
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        if provider == "gemini":
            self.backend = GeminiBackend()
        else:
            self.backend = OpenAIBackend(os.environ.get("OPENAI_MODEL", "gpt-4o"))

    def run(self, user_message: str, on_tool_call=None, on_tool_result=None) -> dict:
        return self.backend.run(
            user_message, on_tool_call=on_tool_call, on_tool_result=on_tool_result
        )
