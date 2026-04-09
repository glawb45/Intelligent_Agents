import json
import os
import time
import sys

# ADD THESE TWO LINES:
from dotenv import load_dotenv

load_dotenv()

# Add the parent directory to the path so we can import the agent
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent import TripPlannerAgent


def run_evaluation(output_file="eval/results/run_results.json"):
    # Ensure results directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open("eval/test_cases.json", "r") as f:
        test_cases = json.load(f)

    agent = TripPlannerAgent()
    results = []

    print(f"Starting evaluation of {len(test_cases)} test cases...\n")

    for tc in test_cases:
        print(f"Testing: {tc['id']}")
        start_time = time.time()

        # Run the agent silently
        response = agent.run(tc["prompt"])
        duration = time.time() - start_time

        itinerary = response.get("itinerary", "").lower()
        error = response.get("error")

        # 1. Constraint Checks (Objective)
        score = 0
        max_score = 3

        if not error:
            # Check if destination is mentioned
            if tc["expected_destination"].lower() in itinerary:
                score += 1

            # Check if expected number of days is structured (e.g. "day 1", "day 5")
            if f"day {tc['expected_days']}" in itinerary:
                score += 1

            # Check if budget was addressed
            if "$" in itinerary or "budget" in itinerary:
                score += 1

        case_result = {
            "id": tc["id"],
            "prompt": tc["prompt"],
            "duration_seconds": round(duration, 2),
            "tool_calls_made": len(response.get("tool_calls", [])),
            "constraint_score": f"{score}/{max_score}",
            "error": error,
            "itinerary_preview": itinerary[:200] + "..." if itinerary else "",
        }

        results.append(case_result)
        print(
            f"  -> Score: {score}/{max_score} | Tools used: {case_result['tool_calls_made']} | Time: {case_result['duration_seconds']}s\n"
        )

        time.sleep(15)

    # Save results
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)

    print(f"Evaluation complete. Results saved to {output_file}")


if __name__ == "__main__":
    run_evaluation()
