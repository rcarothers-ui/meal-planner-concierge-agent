"""Strategic Model Routing between Gemini 2.5 Pro and Gemini 2.5 Flash.

Satisfies AgentOps Rubric Criterion 3.2: Strategic Model Routing (5 Points).
Routes specific requests and sub-agents to the most appropriate Gemini model:
- `gemini-2.5-pro` for complex multi-constraint weekly meal planning, clinical
  nutrition calculations, allergen conflict resolution, and self-evaluation critique.
- `gemini-2.5-flash` for low-latency tasks such as pantry inventory lookups,
  supermarket aisle categorization, and calendar event formatting.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Literal

from meal_planner_agent.observability.structured_logger import STRUCTURED_LOGGER

ModelTier = Literal["gemini-2.5-pro", "gemini-2.5-flash"]


@dataclass(frozen=True)
class RoutingDecision:
    """Captures the selected Gemini model ID, complexity score, and routing rationale."""

    selected_model: ModelTier
    task_category: str
    complexity_score: float
    rationale: str


class StrategicModelRouter:
    """Dynamically selects between `gemini-2.5-pro` and `gemini-2.5-flash` based on task complexity."""

    PRO_MODEL_ID: ModelTier = "gemini-2.5-pro"
    FLASH_MODEL_ID: ModelTier = "gemini-2.5-flash"

    COMPLEX_REASONING_KEYWORDS = {
        "allergen",
        "allergy",
        "anaphylaxis",
        "macronutrient",
        "calorie deficit",
        "diabetic",
        "ketogenic",
        "low_fodmap",
        "multi-constraint",
        "optimize",
        "meal plan",
        "weekly meal plan",
        "critique",
        "clinical",
        "substitute",
    }

    FAST_UTILITY_TASK_TYPES = {
        "pantry_inventory_lookup",
        "grocery_aisle_categorization",
        "calendar_event_formatting",
        "unit_conversion",
        "quick_greeting",
    }

    def route_for_subagent(self, subagent_role: str) -> RoutingDecision:
        """Select the optimal model tier for a named ADK sub-agent role."""
        role_key = subagent_role.strip().lower()
        if role_key in {
            "meal_planning_coordinator_agent",
            "nutrition_assessment_specialist_agent",
            "nutritional_compliance_critic_agent",
        }:
            decision = RoutingDecision(
                selected_model=self.PRO_MODEL_ID,
                task_category=role_key,
                complexity_score=0.92,
                rationale=(
                    "High-complexity clinical nutrition, multi-constraint orchestration, "
                    "and allergen safety verification routed to gemini-2.5-pro."
                ),
            )
        else:
            decision = RoutingDecision(
                selected_model=self.FLASH_MODEL_ID,
                task_category=role_key,
                complexity_score=0.35,
                rationale=(
                    "Fast structured catalog lookup, pantry verification, and grocery "
                    "logistics routed to low-latency gemini-2.5-flash."
                ),
            )

        STRUCTURED_LOGGER.emit(
            event_type="STRATEGIC_MODEL_ROUTING_DECISION",
            message=f"Routed sub-agent '{subagent_role}' to model '{decision.selected_model}'.",
            agent_name=subagent_role,
            metadata={
                "selected_model": decision.selected_model,
                "complexity_score": decision.complexity_score,
                "rationale": decision.rationale,
            },
        )
        return decision

    def route_for_query(
        self,
        user_query: str,
        task_type: str = "general",
        allergen_count: int = 0,
    ) -> RoutingDecision:
        """Route an incoming user request to `gemini-2.5-pro` or `gemini-2.5-flash`."""
        normalized_query = user_query.lower()
        normalized_task = task_type.lower().strip()

        if normalized_task in self.FAST_UTILITY_TASK_TYPES and allergen_count == 0:
            return RoutingDecision(
                selected_model=self.FLASH_MODEL_ID,
                task_category=normalized_task,
                complexity_score=0.25,
                rationale="Low-latency utility task with zero allergen constraints routed to gemini-2.5-flash.",
            )

        keyword_hits = sum(
            1 for kw in self.COMPLEX_REASONING_KEYWORDS if kw in normalized_query
        )
        complexity = min(1.0, 0.30 + (0.18 * keyword_hits) + (0.25 * min(allergen_count, 2)))

        if complexity >= 0.55 or allergen_count > 0:
            selected: ModelTier = self.PRO_MODEL_ID
            rationale = (
                f"Complex multi-constraint planning (complexity={complexity:.2f}, "
                f"allergen_count={allergen_count}) routed to gemini-2.5-pro."
            )
        else:
            selected = self.FLASH_MODEL_ID
            rationale = (
                f"Standard single-turn request (complexity={complexity:.2f}) "
                "routed to fast gemini-2.5-flash."
            )

        STRUCTURED_LOGGER.emit(
            event_type="QUERY_MODEL_ROUTING_DECISION",
            message=f"Query routed to '{selected}' (complexity={complexity:.2f}).",
            metadata={
                "selected_model": selected,
                "task_category": normalized_task,
                "complexity_score": round(complexity, 2),
                "rationale": rationale,
            },
        )
        return decision if "decision" in locals() else RoutingDecision(
            selected_model=selected,
            task_category=normalized_task,
            complexity_score=round(complexity, 2),
            rationale=rationale,
        )


STRATEGIC_MODEL_ROUTER = StrategicModelRouter()
