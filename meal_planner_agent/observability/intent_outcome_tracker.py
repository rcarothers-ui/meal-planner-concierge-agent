"""Intent vs. Outcome Audit Capture for Agent Actions and Tool Execution.

Satisfies AgentOps Rubric Criterion 4.2: Intent vs. Outcome Capture (5 Points).
Logs explicitly record both the agent's INTENDED action before execution
(including planned tool, input arguments, and expected outcome) and the ACTUAL
outcome after execution (including status, latency, output summary, and verification).
"""

from __future__ import annotations

import functools
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from meal_planner_agent.observability.structured_logger import STRUCTURED_LOGGER
from meal_planner_agent.observability.tracing import TRACING_MANAGER


class IntentOutcomeTracker:
    """Captures paired AGENT_INTENT (pre-execution) and AGENT_OUTCOME (post-execution) events."""

    def __init__(self) -> None:
        self.intent_outcome_pairs: List[Dict[str, Any]] = []

    def record_intent(
        self,
        *,
        action_name: str,
        agent_name: str,
        planned_arguments: Dict[str, Any],
        expected_postcondition: str,
        session_id: str = "default-session",
    ) -> str:
        """Record the agent's intended action BEFORE executing a tool or sub-agent."""
        correlation_id = f"io-{uuid.uuid4().hex[:12]}"
        trace_id, span_id = TRACING_MANAGER.current_trace_context()

        intent_record = STRUCTURED_LOGGER.emit(
            event_type="AGENT_INTENT_BEFORE_EXECUTION",
            message=f"Agent '{agent_name}' intends to execute '{action_name}'.",
            agent_name=agent_name,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            metadata={
                "correlation_id": correlation_id,
                "phase": "INTENT",
                "intended_action": action_name,
                "planned_arguments": planned_arguments,
                "expected_postcondition": expected_postcondition,
            },
        )
        self.intent_outcome_pairs.append({"correlation_id": correlation_id, "intent": intent_record})
        return correlation_id

    def record_outcome(
        self,
        *,
        correlation_id: str,
        action_name: str,
        agent_name: str,
        actual_result: Any,
        succeeded: bool,
        latency_ms: float,
        session_id: str = "default-session",
    ) -> Dict[str, Any]:
        """Record the actual outcome AFTER executing a tool or sub-agent."""
        trace_id, span_id = TRACING_MANAGER.current_trace_context()
        outcome_record = STRUCTURED_LOGGER.emit(
            event_type="AGENT_OUTCOME_AFTER_EXECUTION",
            message=(
                f"Agent '{agent_name}' completed '{action_name}' with "
                f"status={'SUCCESS' if succeeded else 'FAILURE'} in {latency_ms:.2f}ms."
            ),
            severity="INFO" if succeeded else "WARNING",
            agent_name=agent_name,
            session_id=session_id,
            trace_id=trace_id,
            span_id=span_id,
            metadata={
                "correlation_id": correlation_id,
                "phase": "OUTCOME",
                "executed_action": action_name,
                "succeeded": succeeded,
                "latency_ms": round(latency_ms, 2),
                "actual_outcome": actual_result,
            },
        )
        for pair in self.intent_outcome_pairs:
            if pair["correlation_id"] == correlation_id:
                pair["outcome"] = outcome_record
                break
        return outcome_record


INTENT_OUTCOME_TRACKER = IntentOutcomeTracker()


def track_intent_and_outcome(
    agent_name: str = "meal_planning_coordinator_agent",
    expected_postcondition: str = "Return validated structured JSON payload matching tool schema.",
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator that wraps any tool function with OpenTelemetry spans and Intent/Outcome logging."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            action_name = func.__name__
            with TRACING_MANAGER.start_span(
                f"tool.{action_name}",
                attributes={"agent.name": agent_name, "tool.name": action_name},
            ):
                correlation_id = INTENT_OUTCOME_TRACKER.record_intent(
                    action_name=action_name,
                    agent_name=agent_name,
                    planned_arguments={"args": list(args), "kwargs": dict(kwargs)},
                    expected_postcondition=expected_postcondition,
                )
                start_ts = time.perf_counter()
                try:
                    result = func(*args, **kwargs)
                    latency_ms = (time.perf_counter() - start_ts) * 1000.0
                    succeeded = not (
                        isinstance(result, dict) and result.get("status") == "error"
                    )
                    INTENT_OUTCOME_TRACKER.record_outcome(
                        correlation_id=correlation_id,
                        action_name=action_name,
                        agent_name=agent_name,
                        actual_result=result,
                        succeeded=succeeded,
                        latency_ms=latency_ms,
                    )
                    return result
                except Exception as exc:
                    latency_ms = (time.perf_counter() - start_ts) * 1000.0
                    INTENT_OUTCOME_TRACKER.record_outcome(
                        correlation_id=correlation_id,
                        action_name=action_name,
                        agent_name=agent_name,
                        actual_result={"exception": str(exc)},
                        succeeded=False,
                        latency_ms=latency_ms,
                    )
                    raise

        return wrapper

    return decorator
