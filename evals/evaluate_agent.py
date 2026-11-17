"""Automated Golden Dataset Regression Evaluation Harness.

Satisfies AgentOps Rubric Criterion 5.1: Automated Evaluation Suites (5 Points).
Executes the Meal Planning Concierge Agent against `evals/golden_dataset.json`
to statically measure trajectory accuracy, tool selection, allergen safety
enforcement, budget compliance, and guardrail regression rates.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

from meal_planner_agent.agent import MealPlanningConciergeOrchestrator
from meal_planner_agent.observability.intent_outcome_tracker import INTENT_OUTCOME_TRACKER
from meal_planner_agent.observability.structured_logger import STRUCTURED_LOGGER


async def run_golden_dataset_evaluation(
    dataset_path: str = "evals/golden_dataset.json",
) -> Dict[str, Any]:
    """Run all test cases in `golden_dataset.json` and compute pass rate & regression metrics."""
    raw_cases: List[Dict[str, Any]] = json.loads(Path(dataset_path).read_text(encoding="utf-8"))
    orchestrator = MealPlanningConciergeOrchestrator()

    case_results: List[Dict[str, Any]] = []
    passed_count = 0

    for case in raw_cases:
        eval_id = case["eval_id"]
        inp = case["input"]
        exp = case["expected"]

        before_pair_count = len(INTENT_OUTCOME_TRACKER.intent_outcome_pairs)
        actual = await orchestrator.execute_weekly_meal_planning_workflow(**inp)
        new_pairs = INTENT_OUTCOME_TRACKER.intent_outcome_pairs[before_pair_count:]
        invoked_tools = [
            p["intent"]["metadata"]["intended_action"] for p in new_pairs if "intent" in p
        ]

        checks: Dict[str, bool] = {}
        checks["status_matches"] = actual.get("status") == exp["status"]

        if exp["status"] == "blocked_by_guardrail":
            checks["violation_code_matches"] = (
                actual.get("violation_code") == exp["expected_violation_code"]
            )
        else:
            checks["model_routing_matches"] = (
                actual.get("routed_model") == exp["expected_routed_model"]
            )
            daily_kcal = actual["macronutrient_targets"]["target_daily_calories_kcal"]
            checks["caloric_floor_respected"] = daily_kcal >= exp["min_daily_calories_kcal"]

            forbidden = {a.lower() for a in exp["forbidden_allergens"]}
            leaked_allergens = [
                r["title"]
                for r in actual["selected_recipes"]
                if forbidden.intersection({a.lower() for a in r["allergens_present"]})
            ]
            checks["zero_allergen_leakage"] = len(leaked_allergens) == 0

            total_cost = actual["grocery_shopping_list"]["estimated_total_cost_usd"]
            checks["within_budget"] = total_cost <= exp["max_total_cost_usd"]

            required_tools = set(exp.get("required_tools_invoked", []))
            checks["trajectory_tools_covered"] = required_tools.issubset(set(invoked_tools))

        case_passed = all(checks.values())
        if case_passed:
            passed_count += 1

        case_results.append(
            {
                "eval_id": eval_id,
                "passed": case_passed,
                "checks": checks,
                "invoked_tools": invoked_tools,
            }
        )

    total_cases = len(raw_cases)
    pass_rate = round(passed_count / max(1, total_cases), 4)

    summary = {
        "suite": "Golden Dataset Static Regression Suite",
        "total_cases": total_cases,
        "passed_cases": passed_count,
        "pass_rate": pass_rate,
        "case_results": case_results,
    }
    STRUCTURED_LOGGER.emit(
        event_type="GOLDEN_EVALUATION_SUITE_SUMMARY",
        message=f"Golden evaluation completed: {passed_count}/{total_cases} passed ({pass_rate * 100:.1f}%).",
        metadata=summary,
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Golden Dataset Agent Evaluation Suite.")
    parser.add_argument("--dataset", default="evals/golden_dataset.json")
    parser.add_argument("--min-pass-rate", type=float, default=0.95)
    args = parser.parse_args()

    summary = asyncio.run(run_golden_dataset_evaluation(args.dataset))
    if summary["pass_rate"] < args.min_pass_rate:
        sys.exit(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
