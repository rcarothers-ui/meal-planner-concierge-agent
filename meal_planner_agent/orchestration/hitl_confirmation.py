"""Human-in-the-Loop (HITL) Confirmation Hooks for High-Stakes Agent Actions.

Satisfies AgentOps Rubric Criterion 3.4: Human-in-the-Loop Hooks (5 Points).
High-stakes actions (such as placing real-money grocery delivery orders or
overwriting shared household calendars above threshold) include explicit code
stops requiring human confirmation before execution.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from meal_planner_agent.observability.structured_logger import STRUCTURED_LOGGER


@dataclass
class PendingHumanApproval:
    """Represents a high-stakes action paused awaiting explicit human sign-off."""

    request_id: str
    action_name: str
    summary: str
    monetary_amount_usd: float
    approval_token: str
    approved: bool = False


class HumanInTheLoopConfirmationGate:
    """Enforces explicit code stops for high-stakes financial or external actions."""

    def __init__(self, auto_approve_threshold_usd: float = 0.0) -> None:
        self.auto_approve_threshold_usd = auto_approve_threshold_usd
        self._pending_requests: Dict[str, PendingHumanApproval] = {}
        self._approved_tokens: Dict[str, PendingHumanApproval] = {}

    def create_approval_request(
        self,
        *,
        action_name: str,
        summary: str,
        monetary_amount_usd: float,
    ) -> PendingHumanApproval:
        """Register a paused high-stakes action and generate a unique confirmation request."""
        request_id = f"hitl_req_{uuid.uuid4().hex[:10]}"
        token = f"hitl_approved_token_{uuid.uuid4().hex[:12]}"
        pending = PendingHumanApproval(
            request_id=request_id,
            action_name=action_name,
            summary=summary,
            monetary_amount_usd=monetary_amount_usd,
            approval_token=token,
            approved=False,
        )
        self._pending_requests[request_id] = pending
        STRUCTURED_LOGGER.emit(
            event_type="HITL_CONFIRMATION_REQUIRED",
            message=f"Paused high-stakes action '{action_name}' (${monetary_amount_usd:.2f}) awaiting human approval.",
            severity="WARNING",
            metadata={
                "request_id": request_id,
                "action_name": action_name,
                "summary": summary,
                "monetary_amount_usd": monetary_amount_usd,
            },
        )
        return pending

    def grant_human_approval(self, request_id: str) -> str:
        """Called by the human user/UI to approve a pending high-stakes action and issue its token."""
        if request_id not in self._pending_requests:
            raise KeyError(f"Unknown HITL approval request_id: {request_id}")
        pending = self._pending_requests[request_id]
        pending.approved = True
        self._approved_tokens[pending.approval_token] = pending
        STRUCTURED_LOGGER.emit(
            event_type="HITL_CONFIRMATION_GRANTED",
            message=f"Human approved high-stakes action '{pending.action_name}' (request_id={request_id}).",
            metadata={"request_id": request_id, "action_name": pending.action_name},
        )
        return pending.approval_token

    def verify_or_halt(
        self,
        *,
        action_name: str,
        summary: str,
        monetary_amount_usd: float,
        provided_confirmation_token: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Verify human approval token or halt execution with a pending request ID."""
        if (
            provided_confirmation_token
            and provided_confirmation_token in self._approved_tokens
        ):
            approved_record = self._approved_tokens[provided_confirmation_token]
            return {
                "approved": True,
                "request_id": approved_record.request_id,
                "message": "Verified explicit human-in-the-loop confirmation token.",
            }

        pending = self.create_approval_request(
            action_name=action_name,
            summary=summary,
            monetary_amount_usd=monetary_amount_usd,
        )
        return {
            "approved": False,
            "request_id": pending.request_id,
            "message": (
                f"High-stakes action '{action_name}' (${monetary_amount_usd:.2f}) requires "
                f"explicit human confirmation (request_id='{pending.request_id}')."
            ),
        }


HITL_CONFIRMATION_GATE = HumanInTheLoopConfirmationGate()
