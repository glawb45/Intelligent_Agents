"""
Trip Planner Agent — core agent loop.

Supports both OpenAI and Anthropic backends.
Set LLM_PROVIDER=openai or LLM_PROVIDER=anthropic in your .env (default: openai).

No LangChain, CrewAI, or other agent frameworks used.
"""

import json
import os
from typing import Callable, Optional

from tools import TOOL_DEFINITIONS, execute_tool

SYSTEM_PROMPT = """You are an expert travel planner with deep knowledge of destinations worldwide.
Your goal is to create detailed, realistic, day-by-day trip itineraries tailored to the user's preferences, budget, and travel dates.

## Your Process
1. **Understand the request**: Extract destination, dates/duration, budget, interests, travel party.
2. **Research**: Use search_web to find top attractions, neighborhoods, food scenes, and insider tips.
3. **Check weather**: Use get_weather_forecast so you can give packing tips and plan indoor/outdoor activities appropriately.
4. **Dive into specifics**: Use get_place_details for key attractions the user should visit.
5. **Validate budget**: Use estimate_travel_costs to confirm the itinerary is realistic for the given budget.
6. **Synthesize**: Write a polished, practical itinerary.

## Itinerary Format
- **Trip Overview**: Destination, dates, duration, budget summary
- **Weather Summary**: What to expect and what to pack
- **Day-by-Day Plan**: Morning / Afternoon / Evening for each day
- **Budget Breakdown**: Estimated daily costs and total
- **Pro Tips**: 3-5 insider tips
- **Getting Around**: Transportation recommendations

## Rules
- ALWAYS call estimate_travel_costs to verify budget feasibility
- ALWAYS call get_weather_forecast if dates are provided
- Make recommendations specific (real place names, not generic suggestions)
- Flag if the budget seems too tight and suggest adjustments
"""


# ── OpenAI backend ────────────────────────────────────────────────


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
        from openai import OpenAI

        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        self.model = model
        self.tool_defs = _openai_tool_defs()

    def run(
        self, user_message, on_tool_call=None, on_tool_result=None, max_iterations=12
    ):
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ]
        tool_call_log = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = self.client.chat.completions.create(
                model=self.model,
                max_tokens=4096,
                tools=self.tool_defs,
                messages=messages,
            )

            choice = response.choices[0]
            msg = choice.message
            messages.append(msg)

            # Done — no more tool calls
            if choice.finish_reason == "stop" or not msg.tool_calls:
                return {
                    "itinerary": msg.content or "",
                    "tool_calls": tool_call_log,
                    "iterations": iteration,
                    "error": None,
                }

            # Execute tool calls
            for tc in msg.tool_calls:
                tool_name = tc.function.name
                tool_input = json.loads(tc.function.arguments)

                if on_tool_call:
                    on_tool_call(tool_name, tool_input)
                print(f"Tool called: {tool_name} | Input: {str(tool_input)[:80]}")
                result = execute_tool(tool_name, tool_input)
                print(f"Tool done: {tool_name} | Success: {result.get('success')}")

                result = execute_tool(tool_name, tool_input)

                if on_tool_result:
                    on_tool_result(tool_name, result)

                tool_call_log.append(
                    {
                        "iteration": iteration,
                        "tool": tool_name,
                        "input": tool_input,
                        "success": result.get("success", True),
                        "result_preview": json.dumps(result)[:300],
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
            "iterations": iteration,
            "error": f"Agent hit max iterations ({max_iterations})",
        }


# ── Anthropic backend ─────────────────────────────────────────────


class AnthropicBackend:
    def __init__(self, model="claude-sonnet-4-6"):
        import anthropic

        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model

    def run(
        self, user_message, on_tool_call=None, on_tool_result=None, max_iterations=12
    ):
        messages = [{"role": "user", "content": user_message}]
        tool_call_log = []
        iteration = 0

        while iteration < max_iterations:
            iteration += 1

            response = self.client.messages.create(
                model=self.model,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFINITIONS,
                messages=messages,
            )

            messages.append({"role": "assistant", "content": response.content})

            if response.stop_reason == "end_turn":
                final_text = next(
                    (b.text for b in response.content if hasattr(b, "text")), ""
                )
                return {
                    "itinerary": final_text,
                    "tool_calls": tool_call_log,
                    "iterations": iteration,
                    "error": None,
                }

            if response.stop_reason == "tool_use":
                tool_result_blocks = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    tool_name, tool_input = block.name, block.input

                    if on_tool_call:
                        on_tool_call(tool_name, tool_input)

                    result = execute_tool(tool_name, tool_input)

                    if on_tool_result:
                        on_tool_result(tool_name, result)

                    tool_call_log.append(
                        {
                            "iteration": iteration,
                            "tool": tool_name,
                            "input": tool_input,
                            "success": result.get("success", True),
                            "result_preview": json.dumps(result)[:300],
                        }
                    )

                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        }
                    )

                messages.append({"role": "user", "content": tool_result_blocks})
                continue

            break

        return {
            "itinerary": "",
            "tool_calls": tool_call_log,
            "iterations": iteration,
            "error": f"Agent stopped unexpectedly after {iteration} iterations",
        }


# ── Unified agent — picks backend from LLM_PROVIDER env var ──────


class TripPlannerAgent:
    def __init__(self):
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        if provider == "anthropic":
            model = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")
            self.backend = AnthropicBackend(model=model)
            self.provider = "anthropic"
        else:
            model = os.environ.get("OPENAI_MODEL", "gpt-4o")
            self.backend = OpenAIBackend(model=model)
            self.provider = "openai"

    def run(
        self,
        user_message: str,
        on_tool_call: Optional[Callable[[str, dict], None]] = None,
        on_tool_result: Optional[Callable[[str, dict], None]] = None,
    ) -> dict:
        return self.backend.run(
            user_message,
            on_tool_call=on_tool_call,
            on_tool_result=on_tool_result,
        )
