"""
Deterministic Policy Engine — FraudGraph AI
============================================
Source of truth: dataset/HHGOA_IEEE/README.md  "Fraud Policy" section (Version 1.0)

Rules R1–R10, approval routes (auto / L1 / L2), action identifiers, and all thresholds
are taken verbatim from the policy document.  Nothing is invented or inferred.

Policy Section 2 — Approval routing
-------------------------------------
  auto  : ALLOW_TRANSACTION, MONITOR_CARD, MONITOR_CONNECTED_CARDS, WARN_CUSTOMER,
           VERIFY_WITH_CUSTOMER, STEP_UP_AUTH, GENERATE_REPORT, CREATE_CASE,
           ESCALATE_TO_ANALYST, CLOSE_NO_FRAUD
  L1    : DECLINE_TRANSACTION ;  BLOCK_CARD when exposure <= 2500
  L2    : BLOCK_CARD when exposure > 2500 ;  BLOCK_ALL_CARDS always ;  FILE_REPORT always

Policy Section 3 — Stopping (Rule 6)
---------------------------------------
  Stop when fraud_probability >= 0.85 or <= 0.15 with >= 2 independent evidence pieces,
  a verification response settles the question, or further steps are unlikely to change decision.

Policy Section 3a — Case vs Report
------------------------------------
  CREATE_CASE  whenever fraud_probability >= 0.30, evidence requested, or customer dispute.
  FILE_REPORT  when fraud confirmed/strongly suspected AND at least one of:
                 exposure > 1000, shared device, connected to another card's fraud,
                 pattern is coordinated / undocumented (R9).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums — exact policy identifiers
# ---------------------------------------------------------------------------

class Action(str, Enum):
    ALLOW_TRANSACTION        = "ALLOW_TRANSACTION"
    DECLINE_TRANSACTION      = "DECLINE_TRANSACTION"
    MONITOR_CARD             = "MONITOR_CARD"
    MONITOR_CONNECTED_CARDS  = "MONITOR_CONNECTED_CARDS"
    WARN_CUSTOMER            = "WARN_CUSTOMER"
    VERIFY_WITH_CUSTOMER     = "VERIFY_WITH_CUSTOMER"
    STEP_UP_AUTH             = "STEP_UP_AUTH"
    BLOCK_CARD               = "BLOCK_CARD"
    BLOCK_ALL_CARDS          = "BLOCK_ALL_CARDS"
    GENERATE_REPORT          = "GENERATE_REPORT"
    CREATE_CASE              = "CREATE_CASE"
    FILE_REPORT              = "FILE_REPORT"
    ESCALATE_TO_ANALYST      = "ESCALATE_TO_ANALYST"
    CLOSE_NO_FRAUD           = "CLOSE_NO_FRAUD"


class ApprovalRoute(str, Enum):
    AUTO = "auto"
    L1   = "L1"
    L2   = "L2"


# Policy Section 2 — canonical approval route mapping
# BLOCK_CARD route depends on exposure; resolved at evaluation time.
_STATIC_ROUTES: Dict[str, ApprovalRoute] = {
    Action.ALLOW_TRANSACTION:       ApprovalRoute.AUTO,
    Action.MONITOR_CARD:            ApprovalRoute.AUTO,
    Action.MONITOR_CONNECTED_CARDS: ApprovalRoute.AUTO,
    Action.WARN_CUSTOMER:           ApprovalRoute.AUTO,
    Action.VERIFY_WITH_CUSTOMER:    ApprovalRoute.AUTO,
    Action.STEP_UP_AUTH:            ApprovalRoute.AUTO,
    Action.GENERATE_REPORT:         ApprovalRoute.AUTO,
    Action.CREATE_CASE:             ApprovalRoute.AUTO,
    Action.ESCALATE_TO_ANALYST:     ApprovalRoute.AUTO,
    Action.CLOSE_NO_FRAUD:          ApprovalRoute.AUTO,
    Action.DECLINE_TRANSACTION:     ApprovalRoute.L1,
    Action.BLOCK_ALL_CARDS:         ApprovalRoute.L2,
    Action.FILE_REPORT:             ApprovalRoute.L2,
}


def get_approval_route(action: Action, exposure_usd: float = 0.0) -> ApprovalRoute:
    """Returns the approval route for an action.  BLOCK_CARD route depends on exposure."""
    if action == Action.BLOCK_CARD:
        return ApprovalRoute.L1 if exposure_usd <= 2500.0 else ApprovalRoute.L2
    return _STATIC_ROUTES.get(action, ApprovalRoute.AUTO)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class RecommendedAction:
    action: str           # exact Action enum value
    route: str            # exact ApprovalRoute enum value
    reason: str           # policy rule citation and rationale


@dataclass
class RuleResult:
    rule_id: str
    triggered: bool
    evidence_used: List[str]
    actions: List[RecommendedAction]
    explanation: str


@dataclass
class InvestigationContext:
    """
    All inputs the policy engine needs.  Every field maps to an explicit policy concept.
    The calling layer is responsible for computing these values from graph evidence.
    """
    # Core signals
    fraud_probability: float              # 0.0–1.0
    exposure_usd: float                   # sum of affected transaction amounts
    signal_count: int                     # number of independent evidence signals
    verdict: str                          # "fraud" | "legitimate" | "uncertain"

    # Evidence from Phase 4 graph tools
    flagged_txn_id: Optional[str] = None
    card_id: Optional[str] = None
    customer_id: Optional[str] = None

    # R1 — single vs multiple signals
    single_signal_only: bool = False      # True if only one signal (e.g. risk score alone)

    # R2/R3 — customer verification outcome
    customer_verified: Optional[bool] = None    # True = confirmed, False = denied, None = not asked
    customer_response_text: str = ""

    # R4 — time since verification request
    hours_since_verification_request: Optional[float] = None
    has_pending_authorization: bool = False

    # R5 — card testing
    card_testing_detected: bool = False
    testing_txns: List[str] = field(default_factory=list)
    larger_purchase_cleared: bool = False          # purchase > $100 already cleared

    # R6 — shared origin ring
    shared_device_cards: List[str] = field(default_factory=list)
    shared_region_cards: List[str] = field(default_factory=list)
    shared_email_cards: List[str] = field(default_factory=list)
    shared_element_description: str = ""

    # R7 — disputed but legitimate recurring charge
    disputed_by_customer: bool = False
    matches_recurring_pattern: bool = False       # same merchant, same amount, monthly

    # R8 — uncertain + exposed
    evidence_conflicts: bool = False

    # R9 — undocumented pattern
    undocumented_pattern_detected: bool = False
    undocumented_pattern_description: str = ""

    # R10 — multi-card fraud confirmation
    confirmed_fraud_card_count: int = 0           # count of customer's cards with confirmed fraud
    credentials_confirmed_compromised: bool = False

    # Open evidence items
    pending_evidence_requests: List[str] = field(default_factory=list)


@dataclass
class PolicyDecision:
    """Complete policy evaluation result — initial and final NBA with explanation."""
    rules_evaluated: List[RuleResult]
    initial_actions: List[RecommendedAction]
    final_actions: List[RecommendedAction]
    what_changed: str
    should_open_case: bool
    should_file_report: bool
    should_stop: bool
    stop_reason: str
    create_case_threshold_met: bool     # fraud_probability >= 0.30 or request or dispute
    file_report_threshold_met: bool


# ---------------------------------------------------------------------------
# Policy Engine
# ---------------------------------------------------------------------------

class PolicyEngine:
    """
    Deterministic rule evaluator for Fraud Policy Version 1.0.
    No LLM is used.  All outputs are derived purely from the InvestigationContext.
    """

    # Thresholds from policy text (Section 6 / R1 / R8 / 3a)
    PROB_THRESHOLD_BLOCK_WITHOUT_VERIFY = 0.70   # R1
    PROB_THRESHOLD_STOP_HIGH            = 0.85   # Section 6
    PROB_THRESHOLD_STOP_LOW             = 0.15   # Section 6
    PROB_THRESHOLD_OPEN_CASE            = 0.30   # Section 3a
    EXPOSURE_THRESHOLD_FILE_REPORT      = 1000.0 # Section 3a / R2
    EXPOSURE_THRESHOLD_R4_ESCALATE      = 500.0  # R4
    MIN_SIGNALS_TO_STOP                 = 2      # Section 6

    def evaluate(
        self,
        ctx: InvestigationContext,
        is_final: bool = False
    ) -> List[RuleResult]:
        """
        Evaluates all applicable policy rules against the context.
        When is_final=False, evaluates initial state (no customer response yet).
        When is_final=True, customer/analyst responses are already in ctx.
        Returns list of RuleResult (one per applicable rule).
        """
        results: List[RuleResult] = []

        results.append(self._eval_r1(ctx, is_final))
        results.append(self._eval_r2(ctx))
        results.append(self._eval_r3(ctx))
        results.append(self._eval_r4(ctx))
        results.append(self._eval_r5(ctx))
        results.append(self._eval_r6(ctx))
        results.append(self._eval_r7(ctx))
        results.append(self._eval_r8(ctx))
        results.append(self._eval_r9(ctx))
        results.append(self._eval_r10(ctx))

        return results

    # ------------------------------------------------------------------
    # R1. Verify before you block on a weak signal.
    # ------------------------------------------------------------------
    def _eval_r1(self, ctx: InvestigationContext, is_final: bool) -> RuleResult:
        """
        Policy: If case rests on a single signal and fraud_probability < 0.70,
        recommend VERIFY_WITH_CUSTOMER or STEP_UP_AUTH before any block.
        """
        rule_id = "R1"
        evidence = []
        actions = []

        triggers = (
            ctx.single_signal_only and
            ctx.fraud_probability < self.PROB_THRESHOLD_BLOCK_WITHOUT_VERIFY and
            ctx.customer_verified is None and
            not is_final
        )

        if triggers:
            evidence.append(f"Single signal only with fraud_probability={ctx.fraud_probability:.2f} < 0.70")
            actions.append(RecommendedAction(
                action=Action.VERIFY_WITH_CUSTOMER,
                route=ApprovalRoute.AUTO,
                reason="R1: probability below 0.70 on single signal; verify before block"
            ))
            explanation = (
                f"R1 triggered: fraud_probability {ctx.fraud_probability:.2f} is below the 0.70 "
                f"threshold and only one independent signal is present. Policy requires verification "
                f"before any blocking action to avoid harming legitimate customers."
            )
        else:
            explanation = (
                f"R1 not triggered: "
                + (f"multiple signals present" if not ctx.single_signal_only else "")
                + (f"probability {ctx.fraud_probability:.2f} >= 0.70" if ctx.fraud_probability >= self.PROB_THRESHOLD_BLOCK_WITHOUT_VERIFY else "")
                + (f"customer already verified" if ctx.customer_verified is not None else "")
            ).strip(": ")

        return RuleResult(
            rule_id=rule_id,
            triggered=triggers,
            evidence_used=evidence,
            actions=actions,
            explanation=explanation
        )

    # ------------------------------------------------------------------
    # R2. Customer denies the transaction.
    # ------------------------------------------------------------------
    def _eval_r2(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Recommend BLOCK_CARD and CREATE_CASE.
        Add FILE_REPORT if exposure > $1,000 or shared device or another card's fraud.
        """
        rule_id = "R2"
        evidence = []
        actions = []
        triggers = ctx.customer_verified is False   # customer DENIED

        if triggers:
            evidence.append("Customer denied the transaction")
            evidence.append(f"Exposure: ${ctx.exposure_usd:.2f}")

            route = get_approval_route(Action.BLOCK_CARD, ctx.exposure_usd)
            actions.append(RecommendedAction(
                action=Action.BLOCK_CARD,
                route=route,
                reason=f"R2: customer denied; exposure ${ctx.exposure_usd:.2f} → route {route}"
            ))
            actions.append(RecommendedAction(
                action=Action.CREATE_CASE,
                route=ApprovalRoute.AUTO,
                reason="R2: customer denied transaction"
            ))

            # FILE_REPORT conditions
            file_report_reasons = []
            if ctx.exposure_usd > self.EXPOSURE_THRESHOLD_FILE_REPORT:
                file_report_reasons.append(f"exposure ${ctx.exposure_usd:.2f} > $1,000")
            if ctx.shared_device_cards:
                file_report_reasons.append(f"shared device with {len(ctx.shared_device_cards)} card(s)")
            if ctx.shared_region_cards or ctx.shared_email_cards:
                file_report_reasons.append("connected to another card's fraud pattern")

            if file_report_reasons:
                evidence.extend(file_report_reasons)
                actions.append(RecommendedAction(
                    action=Action.FILE_REPORT,
                    route=ApprovalRoute.L2,
                    reason=f"R2: {'; '.join(file_report_reasons)}"
                ))

            if ctx.shared_device_cards:
                actions.append(RecommendedAction(
                    action=Action.MONITOR_CONNECTED_CARDS,
                    route=ApprovalRoute.AUTO,
                    reason=f"R2: shared device profile across {len(ctx.shared_device_cards)} card(s)"
                ))

            explanation = f"R2 triggered: customer denied transaction. {'; '.join(evidence)}."
        else:
            explanation = "R2 not triggered: customer has not denied the transaction."

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R3. Customer confirms the transaction.
    # ------------------------------------------------------------------
    def _eval_r3(self, ctx: InvestigationContext) -> RuleResult:
        """Policy: Recommend CLOSE_NO_FRAUD. Note confirmation in case file."""
        rule_id = "R3"
        evidence = []
        actions = []
        triggers = ctx.customer_verified is True   # customer CONFIRMED

        if triggers:
            evidence.append("Customer confirmed the transaction")
            actions.append(RecommendedAction(
                action=Action.CLOSE_NO_FRAUD,
                route=ApprovalRoute.AUTO,
                reason="R3: customer confirmed the transaction"
            ))
            explanation = "R3 triggered: customer confirmed transaction; close as no fraud."
        else:
            explanation = "R3 not triggered: customer has not confirmed the transaction."

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R4. No reply within 24 hours.
    # ------------------------------------------------------------------
    def _eval_r4(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Recommend MONITOR_CARD and DECLINE_TRANSACTION for pending auths.
        Escalate if exposure > $500.
        """
        rule_id = "R4"
        evidence = []
        actions = []

        hours = ctx.hours_since_verification_request
        triggers = hours is not None and hours >= 24.0

        if triggers:
            evidence.append(f"No customer reply after {hours:.0f} hours (> 24h threshold)")
            actions.append(RecommendedAction(
                action=Action.MONITOR_CARD,
                route=ApprovalRoute.AUTO,
                reason="R4: no reply within 24 hours"
            ))
            if ctx.has_pending_authorization:
                actions.append(RecommendedAction(
                    action=Action.DECLINE_TRANSACTION,
                    route=ApprovalRoute.L1,
                    reason="R4: pending authorization declined due to no reply"
                ))
            if ctx.exposure_usd > self.EXPOSURE_THRESHOLD_R4_ESCALATE:
                evidence.append(f"Exposure ${ctx.exposure_usd:.2f} > $500 threshold")
                actions.append(RecommendedAction(
                    action=Action.ESCALATE_TO_ANALYST,
                    route=ApprovalRoute.AUTO,
                    reason=f"R4: exposure ${ctx.exposure_usd:.2f} exceeds $500 escalation threshold"
                ))
            explanation = f"R4 triggered: {'; '.join(evidence)}."
        else:
            explanation = (
                f"R4 not triggered: "
                f"{'no verification requested' if hours is None else f'only {hours:.0f}h elapsed (< 24h)'}"
            )

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R5. Card testing.
    # ------------------------------------------------------------------
    def _eval_r5(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: >= 3 small online auths within 1 hour, then a larger purchase.
        Recommend DECLINE_TRANSACTION + STEP_UP_AUTH.
        If purchase > $100 already cleared: recommend BLOCK_CARD instead.
        """
        rule_id = "R5"
        evidence = []
        actions = []
        triggers = ctx.card_testing_detected

        if triggers:
            evidence.append(
                f"Card testing sequence detected: {len(ctx.testing_txns)} small authorizations"
            )
            if ctx.testing_txns:
                evidence.append(f"Testing transactions: {ctx.testing_txns}")

            if ctx.larger_purchase_cleared:
                evidence.append("Larger purchase (> $100) already cleared")
                route = get_approval_route(Action.BLOCK_CARD, ctx.exposure_usd)
                actions.append(RecommendedAction(
                    action=Action.BLOCK_CARD,
                    route=route,
                    reason=f"R5: purchase over $100 already cleared; block card (exposure ${ctx.exposure_usd:.2f})"
                ))
                actions.append(RecommendedAction(
                    action=Action.CREATE_CASE,
                    route=ApprovalRoute.AUTO,
                    reason="R5: confirmed testing sequence with cleared purchase"
                ))
            else:
                actions.append(RecommendedAction(
                    action=Action.DECLINE_TRANSACTION,
                    route=ApprovalRoute.L1,
                    reason="R5: card testing sequence observed"
                ))
                actions.append(RecommendedAction(
                    action=Action.STEP_UP_AUTH,
                    route=ApprovalRoute.AUTO,
                    reason="R5: require step-up authentication before further activity"
                ))
            explanation = f"R5 triggered: {'; '.join(evidence)}."
        else:
            explanation = "R5 not triggered: no card testing sequence detected."

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R6. Shared origin.
    # ------------------------------------------------------------------
    def _eval_r6(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Multiple cards showing fraud from same device, region, or email.
        Recommend CREATE_CASE, FILE_REPORT, MONITOR_CONNECTED_CARDS.
        """
        rule_id = "R6"
        evidence = []
        actions = []

        all_shared = set(ctx.shared_device_cards) | set(ctx.shared_region_cards) | set(ctx.shared_email_cards)
        triggers = len(all_shared) > 0 and ctx.fraud_probability >= 0.30

        if triggers:
            if ctx.shared_device_cards:
                evidence.append(
                    f"Shared device profile across {len(ctx.shared_device_cards)} connected card(s): "
                    f"{', '.join(ctx.shared_device_cards[:5])}"
                )
            if ctx.shared_region_cards:
                evidence.append(f"Shared billing region across {len(ctx.shared_region_cards)} card(s)")
            if ctx.shared_email_cards:
                evidence.append(f"Shared recipient email across {len(ctx.shared_email_cards)} card(s)")
            if ctx.shared_element_description:
                evidence.append(f"Shared element: {ctx.shared_element_description}")

            actions.append(RecommendedAction(
                action=Action.CREATE_CASE,
                route=ApprovalRoute.AUTO,
                reason=f"R6: shared origin identified across {len(all_shared)} card(s)"
            ))
            actions.append(RecommendedAction(
                action=Action.FILE_REPORT,
                route=ApprovalRoute.L2,
                reason=f"R6: coordinated fraud activity from shared origin"
            ))
            actions.append(RecommendedAction(
                action=Action.MONITOR_CONNECTED_CARDS,
                route=ApprovalRoute.AUTO,
                reason=f"R6: monitoring {len(all_shared)} card(s) sharing the same origin"
            ))
            explanation = f"R6 triggered: {'; '.join(evidence)}."
        else:
            explanation = "R6 not triggered: no shared origin with fraud across multiple cards detected."

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R7. Disputed but legitimate.
    # ------------------------------------------------------------------
    def _eval_r7(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Customer disputes charge matching own recurring pattern.
        Recommend CREATE_CASE, VERIFY_WITH_CUSTOMER, WARN_CUSTOMER. Do not block.
        """
        rule_id = "R7"
        evidence = []
        actions = []
        triggers = ctx.disputed_by_customer and ctx.matches_recurring_pattern

        if triggers:
            evidence.append("Customer disputed a charge")
            evidence.append("Charge matches cardholder's own recurring pattern (same merchant/amount/monthly)")
            actions.append(RecommendedAction(
                action=Action.CREATE_CASE,
                route=ApprovalRoute.AUTO,
                reason="R7: customer dispute on likely recurring charge"
            ))
            actions.append(RecommendedAction(
                action=Action.VERIFY_WITH_CUSTOMER,
                route=ApprovalRoute.AUTO,
                reason="R7: verify whether customer recognizes the recurring charge"
            ))
            actions.append(RecommendedAction(
                action=Action.WARN_CUSTOMER,
                route=ApprovalRoute.AUTO,
                reason="R7: send informational message about recurring charge"
            ))
            explanation = "R7 triggered: disputed charge matches recurring pattern — do not block."
        else:
            explanation = (
                "R7 not triggered: "
                + ("no customer dispute" if not ctx.disputed_by_customer else "dispute does not match recurring pattern")
            )

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R8. Escalate when uncertain and exposed.
    # ------------------------------------------------------------------
    def _eval_r8(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: verdict is 'uncertain' and exposure > $500, or evidence conflicts.
        Recommend ESCALATE_TO_ANALYST.
        """
        rule_id = "R8"
        evidence = []
        actions = []

        uncertain_and_exposed = (
            ctx.verdict == "uncertain" and ctx.exposure_usd > self.EXPOSURE_THRESHOLD_R4_ESCALATE
        )
        triggers = uncertain_and_exposed or ctx.evidence_conflicts

        if triggers:
            if uncertain_and_exposed:
                evidence.append(
                    f"Verdict is 'uncertain' with exposure ${ctx.exposure_usd:.2f} > $500"
                )
            if ctx.evidence_conflicts:
                evidence.append("Evidence conflicts detected")
            actions.append(RecommendedAction(
                action=Action.ESCALATE_TO_ANALYST,
                route=ApprovalRoute.AUTO,
                reason=f"R8: {'; '.join(evidence)}"
            ))
            explanation = f"R8 triggered: {'; '.join(evidence)}."
        else:
            explanation = (
                f"R8 not triggered: verdict='{ctx.verdict}', "
                f"exposure=${ctx.exposure_usd:.2f}, conflicts={ctx.evidence_conflicts}"
            )

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R9. Undocumented patterns.
    # ------------------------------------------------------------------
    def _eval_r9(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Activity fits none of the known patterns but shows coordinated/repeated abuse.
        Recommend CREATE_CASE, FILE_REPORT, ESCALATE_TO_ANALYST.
        """
        rule_id = "R9"
        evidence = []
        actions = []
        triggers = ctx.undocumented_pattern_detected

        if triggers:
            evidence.append("Activity does not match any of the 5 documented fraud patterns")
            if ctx.undocumented_pattern_description:
                evidence.append(f"Description: {ctx.undocumented_pattern_description}")
            actions.append(RecommendedAction(
                action=Action.CREATE_CASE,
                route=ApprovalRoute.AUTO,
                reason="R9: undocumented coordinated abuse pattern"
            ))
            actions.append(RecommendedAction(
                action=Action.FILE_REPORT,
                route=ApprovalRoute.L2,
                reason="R9: undocumented pattern — regulatory filing required"
            ))
            actions.append(RecommendedAction(
                action=Action.ESCALATE_TO_ANALYST,
                route=ApprovalRoute.AUTO,
                reason="R9: novel pattern requires human analyst review"
            ))
            explanation = f"R9 triggered: undocumented pattern detected. {'; '.join(evidence)}."
        else:
            explanation = "R9 not triggered: activity matches known patterns or no coordinated abuse evident."

        return RuleResult(
            rule_id=rule_id, triggered=triggers,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # R10. Never BLOCK_ALL_CARDS unless...
    # ------------------------------------------------------------------
    def _eval_r10(self, ctx: InvestigationContext) -> RuleResult:
        """
        Policy: Never BLOCK_ALL_CARDS unless >= 2 cards confirmed fraud OR
        customer credentials confirmed compromised.
        If the call-site requests BLOCK_ALL_CARDS without meeting this, record the violation.
        """
        rule_id = "R10"
        evidence = []
        actions = []

        block_all_justified = (
            ctx.confirmed_fraud_card_count >= 2 or
            ctx.credentials_confirmed_compromised
        )

        if block_all_justified:
            evidence.append(
                f"{'≥2 cards confirmed fraud' if ctx.confirmed_fraud_card_count >= 2 else ''}"
                f"{'credentials confirmed compromised' if ctx.credentials_confirmed_compromised else ''}"
            )
            actions.append(RecommendedAction(
                action=Action.BLOCK_ALL_CARDS,
                route=ApprovalRoute.L2,
                reason=f"R10: condition met — {'; '.join(e for e in evidence if e)}"
            ))
            triggered = True
            explanation = f"R10 triggered: BLOCK_ALL_CARDS justified. {'; '.join(e for e in evidence if e)}."
        else:
            triggered = False
            explanation = (
                f"R10: BLOCK_ALL_CARDS NOT justified. "
                f"confirmed_fraud_card_count={ctx.confirmed_fraud_card_count}, "
                f"credentials_compromised={ctx.credentials_confirmed_compromised}. "
                f"Do not issue BLOCK_ALL_CARDS."
            )

        return RuleResult(
            rule_id=rule_id, triggered=triggered,
            evidence_used=evidence, actions=actions, explanation=explanation
        )

    # ------------------------------------------------------------------
    # Helper: Open Case Threshold (Policy Section 3a)
    # ------------------------------------------------------------------
    def _should_open_case(self, ctx: InvestigationContext) -> bool:
        return (
            ctx.fraud_probability >= self.PROB_THRESHOLD_OPEN_CASE or
            len(ctx.pending_evidence_requests) > 0 or
            ctx.disputed_by_customer
        )

    # ------------------------------------------------------------------
    # Helper: File Report Threshold (Policy Section 3a)
    # ------------------------------------------------------------------
    def _should_file_report(self, ctx: InvestigationContext) -> bool:
        if ctx.verdict not in ("fraud",) and ctx.fraud_probability < 0.70:
            return False
        return (
            ctx.exposure_usd > self.EXPOSURE_THRESHOLD_FILE_REPORT or
            bool(ctx.shared_device_cards) or
            bool(ctx.shared_region_cards) or
            bool(ctx.shared_email_cards) or
            ctx.undocumented_pattern_detected
        )

    # ------------------------------------------------------------------
    # Helper: Stopping Criteria (Policy Section 6)
    # ------------------------------------------------------------------
    def _should_stop(self, ctx: InvestigationContext) -> tuple[bool, str]:
        if ctx.fraud_probability >= self.PROB_THRESHOLD_STOP_HIGH and ctx.signal_count >= self.MIN_SIGNALS_TO_STOP:
            return True, (
                f"Fraud probability {ctx.fraud_probability:.2f} >= 0.85 with "
                f"{ctx.signal_count} independent evidence signals (Section 6)"
            )
        if ctx.fraud_probability <= self.PROB_THRESHOLD_STOP_LOW and ctx.signal_count >= self.MIN_SIGNALS_TO_STOP:
            return True, (
                f"Fraud probability {ctx.fraud_probability:.2f} <= 0.15 with "
                f"{ctx.signal_count} independent evidence signals (Section 6)"
            )
        if ctx.customer_verified is True:
            return True, "Customer confirmed the transaction (Section 6 — verification settles the question)"
        if ctx.customer_verified is False and ctx.fraud_probability >= 0.70:
            return True, "Customer denied transaction and fraud probability is high (Section 6)"
        return False, ""

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------
    def decide(
        self,
        initial_ctx: InvestigationContext,
        final_ctx: Optional[InvestigationContext] = None
    ) -> PolicyDecision:
        """
        Runs full deterministic policy evaluation.
        initial_ctx : context before any evidence was gathered / customer contacted
        final_ctx   : context after evidence responses received (optional)

        Returns PolicyDecision with initial_actions, final_actions, and what_changed.
        """
        # --- Initial evaluation ---
        initial_rules = self.evaluate(initial_ctx, is_final=False)
        initial_actions = self._collect_actions(initial_rules)

        # Add CREATE_CASE to initial if threshold met
        should_open_case_initial = self._should_open_case(initial_ctx)
        if should_open_case_initial and not any(a.action == Action.CREATE_CASE for a in initial_actions):
            initial_actions.append(RecommendedAction(
                action=Action.CREATE_CASE,
                route=ApprovalRoute.AUTO,
                reason="Section 3a: fraud_probability >= 0.30 or evidence requested"
            ))

        # --- Final evaluation ---
        effective_final_ctx = final_ctx if final_ctx is not None else initial_ctx
        should_open_case_final = self._should_open_case(effective_final_ctx)
        should_file_report_final = self._should_file_report(effective_final_ctx)
        stop, stop_reason = self._should_stop(effective_final_ctx)

        if final_ctx is None:
            final_actions = list(initial_actions)
            what_changed = "nothing"
        else:
            final_rules = self.evaluate(effective_final_ctx, is_final=True)
            final_actions = self._collect_actions(final_rules)

            if should_open_case_final and not any(a.action == Action.CREATE_CASE for a in final_actions):
                final_actions.append(RecommendedAction(
                    action=Action.CREATE_CASE,
                    route=ApprovalRoute.AUTO,
                    reason="Section 3a: fraud_probability >= 0.30"
                ))
            if should_file_report_final and not any(a.action == Action.FILE_REPORT for a in final_actions):
                final_actions.append(RecommendedAction(
                    action=Action.FILE_REPORT,
                    route=ApprovalRoute.L2,
                    reason="Section 3a: fraud confirmed/strongly suspected with qualifying conditions"
                ))

            # --- what_changed ---
            initial_action_names = {a.action for a in initial_actions}
            final_action_names   = {a.action for a in final_actions}
            added   = final_action_names - initial_action_names
            removed = initial_action_names - final_action_names

            if not added and not removed:
                what_changed = "Evidence received but recommendation unchanged."
            else:
                parts = []
                if added:
                    parts.append(f"Added: {', '.join(sorted(added))}")
                if removed:
                    parts.append(f"Removed: {', '.join(sorted(removed))}")
                if effective_final_ctx.customer_verified is False and initial_ctx.customer_verified is None:
                    parts.append("Customer denied the transaction, confirming fraud and elevating actions.")
                elif effective_final_ctx.customer_verified is True and initial_ctx.customer_verified is None:
                    parts.append("Customer confirmed the transaction, clearing the alert.")
                elif effective_final_ctx.fraud_probability > initial_ctx.fraud_probability:
                    parts.append(
                        f"Fraud probability rose from {initial_ctx.fraud_probability:.2f} "
                        f"to {effective_final_ctx.fraud_probability:.2f}."
                    )
                what_changed = " ".join(parts)

        all_rules = initial_rules  # expose initial rule set in decision

        return PolicyDecision(
            rules_evaluated=all_rules,
            initial_actions=initial_actions,
            final_actions=final_actions,
            what_changed=what_changed,
            should_open_case=should_open_case_final,
            should_file_report=should_file_report_final,
            should_stop=stop,
            stop_reason=stop_reason,
            create_case_threshold_met=should_open_case_final,
            file_report_threshold_met=should_file_report_final
        )

    def _collect_actions(self, rule_results: List[RuleResult]) -> List[RecommendedAction]:
        """Flattens rule results into a deduplicated action list."""
        seen = set()
        actions = []
        for rr in rule_results:
            if rr.triggered:
                for a in rr.actions:
                    if a.action not in seen:
                        seen.add(a.action)
                        actions.append(a)
        return actions

    def format_nba(self, actions: List[RecommendedAction]) -> List[Dict[str, str]]:
        """Formats actions into the exact answer-file JSON schema."""
        return [
            {"action": a.action, "route": a.route, "reason": a.reason}
            for a in actions
        ]
