"""Human-in-the-loop review logic for the Clinical Trial Agent.

Provides both an interactive (CLI) mode and an API-compatible auto-approve
mode.  In production, the API mode would be replaced by a webhook / UI
that collects the reviewer's decision asynchronously.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from app.core.exceptions import HumanReviewError
from app.core.logging import get_logger

ACTION_APPROVE: str = "approve"
ACTION_REJECT: str = "reject"
ACTION_REQUEST_CHANGES: str = "request_changes"

logger = get_logger(__name__)

_VALID_ACTIONS = {ACTION_APPROVE, ACTION_REJECT, ACTION_REQUEST_CHANGES}


class HumanReviewer:
    """Encapsulates human-in-the-loop review logic.

    Args:
        mode: One of ``"interactive"`` (CLI prompts) or ``"api"``
              (auto-approve, suitable for headless / test runs).
        default_action: Action to use in API mode.
        default_feedback: Feedback string to use in API mode.
    """

    def __init__(
        self,
        mode: str = "api",
        default_action: str = ACTION_APPROVE,
        default_feedback: str = "Auto-approved via API pipeline.",
    ) -> None:
        if mode not in ("interactive", "api"):
            raise ValueError(f"Invalid reviewer mode: {mode!r}")
        self._mode = mode
        self._default_action = default_action
        self._default_feedback = default_feedback

    def solicit_review(
        self,
        feasibility_score: float,
        compliance_flags: List[str],
        risk_summary: Dict[str, float],
    ) -> Tuple[str, str]:
        """Present trial summary and collect a review decision.

        Args:
            feasibility_score: Aggregate feasibility score.
            compliance_flags: Active compliance issues.
            risk_summary: Entity → risk score mapping.

        Returns:
            A tuple of (approval_status, human_feedback).

        Raises:
            HumanReviewError: When the review interaction fails.
        """
        if self._mode == "interactive":
            return self._interactive_review(feasibility_score, compliance_flags, risk_summary)
        return self._api_review(feasibility_score, compliance_flags, risk_summary)

    # ── Interactive (CLI) mode ───────────────────────────────────────────

    def _interactive_review(
        self,
        feasibility_score: float,
        compliance_flags: List[str],
        risk_summary: Dict[str, float],
    ) -> Tuple[str, str]:
        """Run an interactive CLI review session."""
        self._print_review_summary(feasibility_score, compliance_flags, risk_summary)
        try:
            action = self._prompt_action()
            feedback = self._prompt_feedback()
        except (EOFError, KeyboardInterrupt) as exc:
            raise HumanReviewError(
                "Human review interrupted.", details={"error": str(exc)}
            ) from exc

        logger.info("Human review (interactive) — action=%s", action)
        return action, feedback

    # ── API (headless) mode ──────────────────────────────────────────────

    def _api_review(
        self,
        feasibility_score: float,
        compliance_flags: List[str],
        risk_summary: Dict[str, float],
    ) -> Tuple[str, str]:
        """Auto-approve in API mode (no human interaction required)."""
        logger.info(
            "Human review (api) — auto action=%s, score=%.4f",
            self._default_action,
            feasibility_score,
        )
        return self._default_action, self._default_feedback

    # ── Helpers ──────────────────────────────────────────────────────────

    @staticmethod
    def _print_review_summary(
        feasibility_score: float,
        compliance_flags: List[str],
        risk_summary: Dict[str, float],
    ) -> None:
        """Print a formatted summary for the reviewer."""
        separator = "=" * 60
        print(f"\n{separator}")
        print("  HUMAN REVIEW — Clinical Trial Feasibility Assessment")
        print(separator)
        print(f"  Feasibility Score : {feasibility_score:.4f}")
        print(f"  Compliance Issues : {len(compliance_flags)}")
        for flag in compliance_flags:
            print(f"    • {flag}")
        print(f"  Risk Entities     : {len(risk_summary)}")
        for entity, score in risk_summary.items():
            print(f"    • {entity}: {score:.4f}")
        print(separator)

    @staticmethod
    def _prompt_action() -> str:
        """Prompt the reviewer for a decision."""
        while True:
            raw = input(
                "\n  Decision [approve / reject / request_changes]: "
            ).strip().lower()
            if raw in _VALID_ACTIONS:
                return raw
            print(f"  Invalid input '{raw}'. Please enter one of: {_VALID_ACTIONS}")

    @staticmethod
    def _prompt_feedback() -> str:
        """Prompt the reviewer for optional feedback."""
        feedback = input("  Feedback (optional, press Enter to skip): ").strip()
        return feedback if feedback else "No additional feedback."
