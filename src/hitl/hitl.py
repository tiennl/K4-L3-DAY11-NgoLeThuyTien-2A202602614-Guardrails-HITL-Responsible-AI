"""
Lab 11 — Optional enrichment: Human-in-the-Loop Design
  (Không chấm — tham khảo. Tóm tắt nộp do scripts/grade.py tự sinh,
   không viết report/*.md tay.)
  - Confidence Router
  - 3 HITL decision points
"""
from dataclasses import dataclass


# ============================================================
# Optional enrichment: ConfidenceRouter (không chấm)
#
# Route agent responses based on confidence scores:
#   - HIGH (>= 0.9): Auto-send to user
#   - MEDIUM (0.7 - 0.9): Queue for human review
#   - LOW (< 0.7): Escalate to human immediately
#
# Special case: if the action is HIGH_RISK (e.g., money transfer,
# account deletion), ALWAYS escalate regardless of confidence.
#
# Implement the route() method.
# ============================================================

HIGH_RISK_ACTIONS = [
    "transfer_money",
    "close_account",
    "change_password",
    "delete_data",
    "update_personal_info",
]


@dataclass
class RoutingDecision:
    """Result of the confidence router."""
    action: str          # "auto_send", "queue_review", "escalate"
    confidence: float
    reason: str
    priority: str        # "low", "normal", "high"
    requires_human: bool


class ConfidenceRouter:
    """Route agent responses based on confidence and risk level.

    Thresholds:
        HIGH:   confidence >= 0.9 -> auto-send
        MEDIUM: 0.7 <= confidence < 0.9 -> queue for review
        LOW:    confidence < 0.7 -> escalate to human

    High-risk actions always escalate regardless of confidence.
    """

    HIGH_THRESHOLD = 0.9
    MEDIUM_THRESHOLD = 0.7

    def route(self, response: str, confidence: float,
              action_type: str = "general") -> RoutingDecision:
        """Route a response based on confidence score and action type.

        Args:
            response: The agent's response text
            confidence: Confidence score between 0.0 and 1.0
            action_type: Type of action (e.g., "general", "transfer_money")

        Returns:
            RoutingDecision with routing action and metadata
        """
        if action_type in HIGH_RISK_ACTIONS:
            return RoutingDecision(
                action="escalate",
                confidence=confidence,
                reason=f"High-risk action: {action_type}",
                priority="high",
                requires_human=True,
            )

        if confidence >= self.HIGH_THRESHOLD:
            return RoutingDecision(
                action="auto_send",
                confidence=confidence,
                reason="High confidence",
                priority="low",
                requires_human=False,
            )

        if confidence >= self.MEDIUM_THRESHOLD:
            return RoutingDecision(
                action="queue_review",
                confidence=confidence,
                reason="Medium confidence — needs review",
                priority="normal",
                requires_human=True,
            )

        return RoutingDecision(
            action="escalate",
            confidence=confidence,
            reason="Low confidence — escalating",
            priority="high",
            requires_human=True,
        )


# ============================================================
# Optional enrichment: 3 HITL decision points (không chấm)
# Không bắt buộc điền. Tóm tắt bài nộp: chạy scripts/grade.py
# (tự sinh lab_report.md) — không viết report tay.
#
# For each decision point, define:
# - trigger: What condition activates this HITL check?
# - hitl_model: Which model? (human-in-the-loop, human-on-the-loop,
#   human-as-tiebreaker)
# - context_needed: What info does the human reviewer need?
# - example: A concrete scenario
# - approval_path: What approve/reject/timeout decision is recorded?
# - audit_fields: Which correlation ID, intent and proposed action/diff are logged?
#
# Think about real banking scenarios where human judgment is critical.
# ============================================================

hitl_decision_points = [
    {
        "id": 1,
        "name": "Outbound money transfer approval",
        "trigger": "Agent proposes a transfer_money action above a small threshold, or to a new/unverified beneficiary.",
        "hitl_model": "human-in-the-loop",
        "context_needed": "Source/destination accounts, amount, currency, beneficiary history, agent's stated intent, any RAG/email content that influenced the decision.",
        "example": "Customer's email mentions 'please wire 500,000,000 VND to this new supplier account'; agent drafts a transfer_money action instead of executing it directly.",
        "approval_path": "Approve -> action executes and is logged with approval_id/reviewer_id. Reject -> action discarded, customer notified. Timeout (no reviewer response within SLA) -> auto-reject, escalate to on-call supervisor.",
        "audit_fields": "correlation_id, user_id, intent, proposed_action (destination + payload diff), reviewer_id, approval_id, decision, decision_timestamp.",
    },
    {
        "id": 2,
        "name": "Credential / secret disclosure request",
        "trigger": "Input or output guardrail flags a request or response touching admin_password, api_key, or db_host (even if ultimately blocked).",
        "hitl_model": "human-on-the-loop",
        "context_needed": "Full conversation transcript, which layer flagged it (input_injection/output_filter), user_id, whether the block was overridden.",
        "example": "A user claiming to be an on-call engineer asks the bot to 'confirm' the admin password for an incident ticket; guardrail blocks it and queues the transcript for security review.",
        "approval_path": "Human reviewer periodically audits the queue (not blocking the user in real time); can flag the account for further investigation or confirm it was a benign false positive.",
        "audit_fields": "correlation_id, user_id, matched_pattern/layer, request_id, reviewer_id, review_outcome, review_timestamp.",
    },
    {
        "id": 3,
        "name": "Low-confidence banking advice",
        "trigger": "ConfidenceRouter scores the agent's answer below the MEDIUM_THRESHOLD (0.7) for a non-high-risk banking question (e.g. ambiguous loan eligibility).",
        "hitl_model": "human-as-tiebreaker",
        "context_needed": "The question, the agent's draft answer, confidence score, and any conflicting source documents (rates table, policy doc).",
        "example": "Customer asks about eligibility for a specific loan product with unusual conditions; agent's confidence is 0.55 because the policy is ambiguous.",
        "approval_path": "Reviewer either approves the draft answer as-is, edits it, or escalates to a specialist. Timeout routes to a generic 'please contact a branch' fallback so the customer is never left waiting indefinitely.",
        "audit_fields": "correlation_id, user_id, intent, draft_response, confidence_score, reviewer_id, final_response, decision_timestamp.",
    },
]


# ============================================================
# Quick tests
# ============================================================

def test_confidence_router():
    """Test ConfidenceRouter with sample scenarios."""
    router = ConfidenceRouter()

    test_cases = [
        ("Balance inquiry", 0.95, "general"),
        ("Interest rate question", 0.82, "general"),
        ("Ambiguous request", 0.55, "general"),
        ("Transfer $50,000", 0.98, "transfer_money"),
        ("Close my account", 0.91, "close_account"),
    ]

    print("Testing ConfidenceRouter:")
    print("=" * 80)
    print(f"{'Scenario':<25} {'Conf':<6} {'Action Type':<18} {'Decision':<15} {'Priority':<10} {'Human?'}")
    print("-" * 80)

    for scenario, conf, action_type in test_cases:
        decision = router.route(scenario, conf, action_type)
        print(
            f"{scenario:<25} {conf:<6.2f} {action_type:<18} "
            f"{decision.action:<15} {decision.priority:<10} "
            f"{'Yes' if decision.requires_human else 'No'}"
        )

    print("=" * 80)


def test_hitl_points():
    """Display HITL decision points."""
    print("\nHITL Decision Points:")
    print("=" * 60)
    for point in hitl_decision_points:
        print(f"\n  Decision Point #{point['id']}: {point['name']}")
        print(f"    Trigger:  {point['trigger']}")
        print(f"    Model:    {point['hitl_model']}")
        print(f"    Context:  {point['context_needed']}")
        print(f"    Example:  {point['example']}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    test_confidence_router()
    test_hitl_points()
