"""
Evaluator for the Trip Planner Agent.

Two-part evaluation:
  A) Constraint Satisfaction Score  — objective, rule-based checks
  B) LLM-as-Judge Score             — subjective quality rubric scored by Claude

Run with:
    python eval/evaluator.py [--cases 1,2,3] [--out eval/results/run.json]
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

# Make sure we can import from project root
sys.path.insert(0, str(Path(__file__).parent.parent))
from agent import TripPlannerAgent


# ─────────────────────────────────────────────────────────────────
# A) Constraint Satisfaction Checker
# ─────────────────────────────────────────────────────────────────

def check_constraints(itinerary: str, constraints: dict) -> dict:
    """
    Programmatically check whether the itinerary satisfies hard constraints.
    Returns a dict of {check_name: bool} and an overall score 0-1.
    """
    text = itinerary.lower()
    checks = {}

    # 1. Destination mentioned
    dest = constraints.get("destination", "").lower()
    checks["destination_mentioned"] = dest in text

    # 2. Correct number of days
    num_days = constraints.get("num_days", 0)
    # Look for "Day N" patterns
    day_matches = re.findall(r'\bday\s+(\d+)\b', text)
    if day_matches:
        max_day = max(int(d) for d in day_matches)
        checks["correct_num_days"] = (max_day == num_days) or (max_day >= num_days - 1)
    else:
        # Fallback: count occurrences of "day"
        checks["correct_num_days"] = len(day_matches) > 0

    # 3. Budget addressed
    checks["budget_addressed"] = any(kw in text for kw in ["budget", "cost", "price", "$", "usd", "per day", "daily"])

    # 4. Interests covered (at least half)
    interests = constraints.get("interests", [])
    if interests:
        covered = sum(1 for i in interests if i.lower() in text)
        checks["interests_covered"] = covered >= max(1, len(interests) // 2)
    else:
        checks["interests_covered"] = True

    # 5. Has day-by-day structure
    checks["has_day_structure"] = bool(re.search(r'\bday\s+[1-9]', text, re.IGNORECASE))

    # 6. Weather mentioned (if start_date was provided)
    if constraints.get("start_date"):
        checks["weather_mentioned"] = any(kw in text for kw in ["weather", "temperature", "rain", "sunny", "pack", "packing", "forecast"])
    else:
        checks["weather_mentioned"] = True  # N/A — not required

    # 7. Transportation mentioned
    checks["transport_mentioned"] = any(kw in text for kw in [
        "metro", "subway", "bus", "train", "taxi", "uber", "walk", "walking",
        "transport", "transit", "getting around", "railway", "tram", "bike", "cycling"
    ])

    # 8. Travel party considered
    party = constraints.get("travel_party", "")
    if party == "family":
        checks["party_considered"] = any(kw in text for kw in ["family", "kid", "child", "children"])
    elif party == "couple":
        checks["party_considered"] = any(kw in text for kw in ["couple", "together", "partner", "romantic"])
    elif party == "solo":
        checks["party_considered"] = any(kw in text for kw in ["solo", "alone", "single traveler", "yourself"])
    else:
        checks["party_considered"] = True

    # Score = fraction of checks passed
    score = sum(checks.values()) / len(checks)
    return {"checks": checks, "score": round(score, 3)}


# ─────────────────────────────────────────────────────────────────
# B) LLM-as-Judge
# ─────────────────────────────────────────────────────────────────

JUDGE_PROMPT = """You are an expert travel critic evaluating an AI-generated trip itinerary.

User's request: {request}

Generated itinerary:
{itinerary}

Score this itinerary on each of the following dimensions from 1 (very poor) to 5 (excellent).
Be strict and honest — reserve 5 for truly exceptional outputs.

Dimensions:
1. coherence       — Is the day-by-day flow logical? Are timings realistic? Does it avoid scheduling impossibilities?
2. specificity     — Does it name real, specific places rather than vague suggestions?
3. budget_fit      — Does the itinerary realistically fit within the stated budget?
4. interest_match  — Does it genuinely cater to the user's stated interests?
5. practicality    — Is the advice actionable? (opening hours, booking tips, transport)?
6. completeness    — Does it cover all days requested and provide a full experience?

Respond ONLY with a JSON object — no preamble, no explanation, no markdown fences:
{{"coherence": X, "specificity": X, "budget_fit": X, "interest_match": X, "practicality": X, "completeness": X, "brief_reason": "one sentence"}}
"""

def llm_judge(itinerary: str, test_case: dict) -> dict:
    """Use Claude to score the itinerary on 6 quality dimensions."""
    client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

    prompt = JUDGE_PROMPT.format(
        request=test_case["input"],
        itinerary=itinerary[:6000]  # truncate to avoid token overrun
    )

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )
        raw = response.content[0].text.strip()
        # Strip any accidental markdown fences
        raw = re.sub(r"```json|```", "", raw).strip()
        scores = json.loads(raw)
        dims = ["coherence", "specificity", "budget_fit", "interest_match", "practicality", "completeness"]
        numeric = {d: scores.get(d, 0) for d in dims}
        avg = sum(numeric.values()) / len(numeric)
        return {
            "scores": numeric,
            "reason": scores.get("brief_reason", ""),
            "average": round(avg, 3),
            "success": True
        }
    except Exception as e:
        return {"scores": {}, "average": 0, "success": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────
# Run evaluation
# ─────────────────────────────────────────────────────────────────

def evaluate_case(test_case: dict) -> dict:
    """Run the agent on one test case and evaluate it."""
    print(f"\n{'='*60}")
    print(f"Test case {test_case['id']}: {test_case['input'][:70]}…")
    print(f"{'='*60}")

    start = time.time()
    agent = TripPlannerAgent()

    tool_calls_made = []

    def on_tool_call(name, inp):
        print(f"  → tool: {name}({list(inp.keys())})")
        tool_calls_made.append(name)

    result = agent.run(test_case["input"], on_tool_call=on_tool_call)
    elapsed = time.time() - start

    itinerary = result.get("itinerary", "")
    if result.get("error"):
        print(f"  ✗ Agent error: {result['error']}")
        return {
            "id": test_case["id"],
            "input": test_case["input"],
            "error": result["error"],
            "elapsed_s": round(elapsed, 1),
        }

    print(f"  ✓ Agent finished in {elapsed:.1f}s ({result['iterations']} iterations, {len(result['tool_calls'])} tool calls)")

    # Constraint satisfaction
    cs = check_constraints(itinerary, test_case["constraints"])
    print(f"  Constraint score: {cs['score']:.2f} ({sum(cs['checks'].values())}/{len(cs['checks'])} checks passed)")

    # LLM judge
    print("  Running LLM judge…")
    judge = llm_judge(itinerary, test_case)
    if judge["success"]:
        print(f"  LLM judge average: {judge['average']:.2f}/5.0")
        print(f"  Reason: {judge.get('reason', '')}")
    else:
        print(f"  LLM judge failed: {judge.get('error')}")

    return {
        "id": test_case["id"],
        "input": test_case["input"],
        "itinerary_length": len(itinerary),
        "elapsed_s": round(elapsed, 1),
        "iterations": result["iterations"],
        "num_tool_calls": len(result["tool_calls"]),
        "tools_used": tool_calls_made,
        "constraint_satisfaction": cs,
        "llm_judge": judge,
        "itinerary_preview": itinerary[:500],
        "itinerary_full": itinerary,
    }


def run_evaluation(case_ids: list = None, output_path: str = None):
    test_cases_path = Path(__file__).parent / "test_cases.json"
    with open(test_cases_path) as f:
        all_cases = json.load(f)

    if case_ids:
        cases = [c for c in all_cases if c["id"] in case_ids]
    else:
        cases = all_cases

    print(f"\n🧪 Running evaluation on {len(cases)} test case(s)…")

    results = []
    for case in cases:
        result = evaluate_case(case)
        results.append(result)
        time.sleep(2)  # be polite to APIs

    # ── Aggregate stats ──────────────────────────────────────────
    valid = [r for r in results if "error" not in r]
    if valid:
        avg_cs = sum(r["constraint_satisfaction"]["score"] for r in valid) / len(valid)
        judge_valid = [r for r in valid if r["llm_judge"]["success"]]
        avg_judge = sum(r["llm_judge"]["average"] for r in judge_valid) / len(judge_valid) if judge_valid else 0

        # Per-dimension averages
        dim_avgs = {}
        dims = ["coherence", "specificity", "budget_fit", "interest_match", "practicality", "completeness"]
        for d in dims:
            vals = [r["llm_judge"]["scores"].get(d, 0) for r in judge_valid if r["llm_judge"]["success"]]
            dim_avgs[d] = round(sum(vals) / len(vals), 2) if vals else 0

        avg_tools = sum(r["num_tool_calls"] for r in valid) / len(valid)
        avg_time = sum(r["elapsed_s"] for r in valid) / len(valid)

        summary = {
            "timestamp": datetime.now().isoformat(),
            "num_cases": len(cases),
            "num_valid": len(valid),
            "avg_constraint_satisfaction": round(avg_cs, 3),
            "avg_llm_judge_score": round(avg_judge, 3),
            "llm_judge_by_dimension": dim_avgs,
            "avg_tool_calls": round(avg_tools, 1),
            "avg_elapsed_s": round(avg_time, 1),
        }

        print(f"\n{'='*60}")
        print("📊 EVALUATION SUMMARY")
        print(f"{'='*60}")
        print(f"  Cases evaluated       : {len(valid)}/{len(cases)}")
        print(f"  Constraint Satisfaction: {avg_cs:.2%}")
        print(f"  LLM Judge (avg/5.0)   : {avg_judge:.2f}")
        print(f"  LLM Judge by dimension:")
        for d, v in dim_avgs.items():
            bar = "█" * int(v) + "░" * (5 - int(v))
            print(f"    {d:<18} {bar} {v:.2f}")
        print(f"  Avg tool calls/trip   : {avg_tools:.1f}")
        print(f"  Avg time/trip (s)     : {avg_time:.1f}")
    else:
        summary = {"error": "No valid results"}

    output = {"summary": summary, "results": results}

    if output_path is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(__file__).parent / "results" / f"eval_{ts}.json"

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Results saved to {output_path}")
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate the Trip Planner Agent")
    parser.add_argument("--cases", type=str, default=None,
                        help="Comma-separated test case IDs to run (e.g. 1,2,3). Runs all if omitted.")
    parser.add_argument("--out", type=str, default=None,
                        help="Output JSON path. Defaults to eval/results/eval_<timestamp>.json")
    args = parser.parse_args()

    case_ids = [int(x) for x in args.cases.split(",")] if args.cases else None
    run_evaluation(case_ids=case_ids, output_path=args.out)
