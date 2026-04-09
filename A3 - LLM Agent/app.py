"""
Flask server for Trip Planner Agent.
Uses SSE with keepalive pings so browser never drops connection.
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


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/api/plan", methods=["POST"])
def plan_trip():
    body = request.get_json(force=True)
    user_message = body.get("message", "").strip()

    if not user_message:
        return jsonify({"error": "No message provided"}), 400

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
            print(f"[agent] Starting for: {user_message[:60]}")
            agent = TripPlannerAgent()
            result = agent.run(
                user_message, on_tool_call=on_tool_call, on_tool_result=on_tool_result
            )
            print(f"[agent] Done. Error = {result.get('error')}")

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
            print(f"[agent] Excpetion: {e}")
            event_queue.put({"type": "error", "message": str(e)})

        finally:
            event_queue.put(None)

    thread = threading.Thread(target=run_agent, daemon=True)
    thread.start()

    def generate():
        while True:
            try:
                # Check for event, keep session alive
                event = event_queue.get(timeout=2)

            except queue.Empty:
                # Send keepalive comment every 2 seconds
                yield ": keepalive\n\n"
                continue

            if event is None:
                break

            print(f"[sse] Sending event: {event.get('type')}")
            yield "data: " + json.dumps(event) + "\n\n"

    return Response(
        generate(),
        mimetype="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    # Define localhost = 5001
    port = int(os.environ.get("PORT", 5001))
    # 1. flush=True forces the text to bypass the buffer and print immediately
    print(f"Trip Planner Agent running at http://127.0.0.1:{port}", flush=True)

    # 2. host="127.0.0.1" bypasses the macOS DNS bug completely
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)
