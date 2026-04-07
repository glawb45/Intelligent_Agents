"""
Flask web server for the Trip Planner Agent.
Serves the frontend and exposes the agent via REST + Server-Sent Events.
"""

import json
import os
import queue
import threading
import time
from flask import Flask, Response, jsonify, request, send_from_directory
from dotenv import load_dotenv

load_dotenv()

from agent import TripPlannerAgent

app = Flask(__name__, static_folder="static")


# ─────────────────────────────────────────────────────────────────
# Static file serving
# ─────────────────────────────────────────────────────────────────


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory("static", filename)


# ─────────────────────────────────────────────────────────────────
# Health check
# ─────────────────────────────────────────────────────────────────


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


# ─────────────────────────────────────────────────────────────────
# Plan trip — streaming via SSE
# ─────────────────────────────────────────────────────────────────


@app.route("/api/plan", methods=["POST"])
def plan_trip():
    """
    Accepts a JSON body: { "message": "..." }
    Streams back server-sent events as the agent works:
      - data: {"type": "tool_call", "tool": "...", "input": {...}}
      - data: {"type": "tool_result", "tool": "...", "success": bool}
      - data: {"type": "complete", "itinerary": "...", "tool_calls": [...], "iterations": N}
      - data: {"type": "error", "message": "..."}
    """
    body = request.get_json(force=True)
    user_message = body.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Queue for SSE events produced by the agent thread
    event_queue = queue.Queue()

    def on_tool_call(tool_name, tool_input):
        event_queue.put({"type": "tool_call", "tool": tool_name, "input": tool_input})

    def on_tool_result(tool_name, result):
        event_queue.put(
            {
                "type": "tool_result",
                "tool": tool_name,
                "success": result.get("success", True),
            }
        )

    def run_agent():
        try:
            print("Agent started...")
            agent = TripPlannerAgent()
            result = agent.run(
                user_message,
                on_tool_call=on_tool_call,
                on_tool_result=on_tool_result,
            )
            if result.get("error"):
                event_queue.put({"type": "error", "message": result["error"]})
            else:
                event_queue.put(
                    {
                        "type": "complete",
                        "itinerary": result["itinerary"],
                        "tool_calls": result["tool_calls"],
                        "iterations": result["iterations"],
                    }
                )
        except Exception as e:
            event_queue.put({"type": "error", "message": str(e)})
        finally:
            event_queue.put(None)  # sentinel

    # Run agent in a background thread so we can stream SSE
    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                event = event_queue.get(timeout=120)
            except queue.Empty:
                yield "data: " + json.dumps(
                    {"type": "error", "message": "Timeout"}
                ) + "\n\n"
                break

            if event is None:
                break

            yield "data: " + json.dumps(event) + "\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    print(f"🌍 Trip Planner Agent running at http://localhost:{port}")
    app.run(debug=False, port=port, threaded=True)
