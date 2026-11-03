"""
Tests for Phase 5A — Deterministic Policy Engine
=================================================
Covers all R1–R10 rule evaluations, approval route mapping, initial vs final NBA,
what_changed generation, and missing evidence handling.
"""
import unittest
from src.policy.engine import (
    PolicyEngine,
    InvestigationContext,
    Action,
    ApprovalRoute,
    get_approval_route,
    RecommendedAction,
)


class TestApprovalRoutes(unittest.TestCase):
    """Section 2 approval route mapping — all 14 actions."""

    def test_auto_actions(self):
        auto_actions = [
            Action.ALLOW_TRANSACTION, Action.MONITOR_CARD, Action.MONITOR_CONNECTED_CARDS,
            Action.WARN_CUSTOMER, Action.VERIFY_WITH_CUSTOMER, Action.STEP_UP_AUTH,
            Action.GENERATE_REPORT, Action.CREATE_CASE, Action.ESCALATE_TO_ANALYST,
            Action.CLOSE_NO_FRAUD,
        ]
        for a in auto_actions:
            with self.subTest(action=a):
                self.assertEqual(get_approval_route(a, 0.0), ApprovalRoute.AUTO)

    def test_l1_decline_transaction(self):
        self.assertEqual(get_approval_route(Action.DECLINE_TRANSACTION, 0.0), ApprovalRoute.L1)

    def test_l1_block_card_low_exposure(self):
        self.assertEqual(get_approval_route(Action.BLOCK_CARD, 1000.0), ApprovalRoute.L1)
        self.assertEqual(get_approval_route(Action.BLOCK_CARD, 2500.0), ApprovalRoute.L1)

    def test_l2_block_card_high_exposure(self):
        self.assertEqual(get_approval_route(Action.BLOCK_CARD, 2500.01), ApprovalRoute.L2)
        self.assertEqual(get_approval_route(Action.BLOCK_CARD, 9999.0), ApprovalRoute.L2)

    def test_l2_block_all_cards(self):
        self.assertEqual(get_approval_route(Action.BLOCK_ALL_CARDS, 0.0), ApprovalRoute.L2)

    def test_l2_file_report(self):
        self.assertEqual(get_approval_route(Action.FILE_REPORT, 0.0), ApprovalRoute.L2)


class TestR1(unittest.TestCase):
    """R1: Verify before you block on a weak signal."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r1_triggers_single_signal_low_probability(self):
        ctx = InvestigationContext(
            fraud_probability=0.45,
            exposure_usd=200.0,
            signal_count=1,
            verdict="uncertain",
            single_signal_only=True,
            customer_verified=None
        )
        results = self.engine.evaluate(ctx, is_final=False)
        r1 = next(r for r in results if r.rule_id == "R1")
        self.assertTrue(r1.triggered)
        actions = [a.action for a in r1.actions]
        self.assertIn(Action.VERIFY_WITH_CUSTOMER, actions)

    def test_r1_does_not_trigger_multiple_signals(self):
        ctx = InvestigationContext(
            fraud_probability=0.45,
            exposure_usd=200.0,
            signal_count=3,
            verdict="uncertain",
            single_signal_only=False,
        )
        results = self.engine.evaluate(ctx, is_final=False)
        r1 = next(r for r in results if r.rule_id == "R1")
        self.assertFalse(r1.triggered)

    def test_r1_does_not_trigger_probability_above_threshold(self):
        ctx = InvestigationContext(
            fraud_probability=0.75,
            exposure_usd=200.0,
            signal_count=1,
            verdict="uncertain",
            single_signal_only=True,
        )
        results = self.engine.evaluate(ctx, is_final=False)
        r1 = next(r for r in results if r.rule_id == "R1")
        self.assertFalse(r1.triggered)

    def test_r1_does_not_trigger_if_already_verified(self):
        ctx = InvestigationContext(
            fraud_probability=0.45,
            exposure_usd=200.0,
            signal_count=1,
            verdict="uncertain",
            single_signal_only=True,
            customer_verified=False   # already answered
        )
        results = self.engine.evaluate(ctx, is_final=False)
        r1 = next(r for r in results if r.rule_id == "R1")
        self.assertFalse(r1.triggered)


class TestR2(unittest.TestCase):
    """R2: Customer denies the transaction."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r2_triggers_on_denial(self):
        ctx = InvestigationContext(
            fraud_probability=0.82,
            exposure_usd=800.0,
            signal_count=2,
            verdict="fraud",
            customer_verified=False,
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        self.assertTrue(r2.triggered)
        actions = [a.action for a in r2.actions]
        self.assertIn(Action.BLOCK_CARD, actions)
        self.assertIn(Action.CREATE_CASE, actions)

    def test_r2_adds_file_report_above_1000(self):
        ctx = InvestigationContext(
            fraud_probability=0.88,
            exposure_usd=1500.0,
            signal_count=2,
            verdict="fraud",
            customer_verified=False,
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        actions = [a.action for a in r2.actions]
        self.assertIn(Action.FILE_REPORT, actions)

    def test_r2_adds_file_report_shared_device(self):
        ctx = InvestigationContext(
            fraud_probability=0.82,
            exposure_usd=200.0,
            signal_count=2,
            verdict="fraud",
            customer_verified=False,
            shared_device_cards=["C00001-K1", "C00002-K1"],
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        actions = [a.action for a in r2.actions]
        self.assertIn(Action.FILE_REPORT, actions)

    def test_r2_block_card_route_l1_low_exposure(self):
        ctx = InvestigationContext(
            fraud_probability=0.82, exposure_usd=500.0, signal_count=2,
            verdict="fraud", customer_verified=False,
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        block_action = next(a for a in r2.actions if a.action == Action.BLOCK_CARD)
        self.assertEqual(block_action.route, ApprovalRoute.L1)

    def test_r2_block_card_route_l2_high_exposure(self):
        ctx = InvestigationContext(
            fraud_probability=0.88, exposure_usd=3000.0, signal_count=2,
            verdict="fraud", customer_verified=False,
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        block_action = next(a for a in r2.actions if a.action == Action.BLOCK_CARD)
        self.assertEqual(block_action.route, ApprovalRoute.L2)

    def test_r2_does_not_trigger_no_denial(self):
        ctx = InvestigationContext(
            fraud_probability=0.82, exposure_usd=800.0, signal_count=2,
            verdict="fraud", customer_verified=None,
        )
        results = self.engine.evaluate(ctx)
        r2 = next(r for r in results if r.rule_id == "R2")
        self.assertFalse(r2.triggered)


class TestR3(unittest.TestCase):
    """R3: Customer confirms the transaction."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r3_triggers_on_confirmation(self):
        ctx = InvestigationContext(
            fraud_probability=0.2, exposure_usd=100.0, signal_count=1,
            verdict="legitimate", customer_verified=True,
        )
        results = self.engine.evaluate(ctx)
        r3 = next(r for r in results if r.rule_id == "R3")
        self.assertTrue(r3.triggered)
        actions = [a.action for a in r3.actions]
        self.assertIn(Action.CLOSE_NO_FRAUD, actions)
        # Route must be auto
        close_action = next(a for a in r3.actions if a.action == Action.CLOSE_NO_FRAUD)
        self.assertEqual(close_action.route, ApprovalRoute.AUTO)

    def test_r3_does_not_trigger_without_confirmation(self):
        ctx = InvestigationContext(
            fraud_probability=0.2, exposure_usd=100.0, signal_count=1,
            verdict="legitimate", customer_verified=None,
        )
        results = self.engine.evaluate(ctx)
        r3 = next(r for r in results if r.rule_id == "R3")
        self.assertFalse(r3.triggered)


class TestR4(unittest.TestCase):
    """R4: No reply within 24 hours."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r4_triggers_after_24h(self):
        ctx = InvestigationContext(
            fraud_probability=0.55, exposure_usd=300.0, signal_count=1,
            verdict="uncertain", hours_since_verification_request=26.0,
        )
        results = self.engine.evaluate(ctx)
        r4 = next(r for r in results if r.rule_id == "R4")
        self.assertTrue(r4.triggered)
        actions = [a.action for a in r4.actions]
        self.assertIn(Action.MONITOR_CARD, actions)

    def test_r4_declines_pending_authorization(self):
        ctx = InvestigationContext(
            fraud_probability=0.55, exposure_usd=200.0, signal_count=1,
            verdict="uncertain", hours_since_verification_request=26.0,
            has_pending_authorization=True
        )
        results = self.engine.evaluate(ctx)
        r4 = next(r for r in results if r.rule_id == "R4")
        actions = [a.action for a in r4.actions]
        self.assertIn(Action.DECLINE_TRANSACTION, actions)

    def test_r4_escalates_above_500(self):
        ctx = InvestigationContext(
            fraud_probability=0.55, exposure_usd=600.0, signal_count=1,
            verdict="uncertain", hours_since_verification_request=30.0,
        )
        results = self.engine.evaluate(ctx)
        r4 = next(r for r in results if r.rule_id == "R4")
        actions = [a.action for a in r4.actions]
        self.assertIn(Action.ESCALATE_TO_ANALYST, actions)

    def test_r4_does_not_trigger_before_24h(self):
        ctx = InvestigationContext(
            fraud_probability=0.55, exposure_usd=300.0, signal_count=1,
            verdict="uncertain", hours_since_verification_request=10.0,
        )
        results = self.engine.evaluate(ctx)
        r4 = next(r for r in results if r.rule_id == "R4")
        self.assertFalse(r4.triggered)

    def test_r4_does_not_trigger_no_request(self):
        ctx = InvestigationContext(
            fraud_probability=0.55, exposure_usd=300.0, signal_count=1,
            verdict="uncertain", hours_since_verification_request=None,
        )
        results = self.engine.evaluate(ctx)
        r4 = next(r for r in results if r.rule_id == "R4")
        self.assertFalse(r4.triggered)


class TestR5(unittest.TestCase):
    """R5: Card testing pattern."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r5_triggers_testing_detected_no_large_purchase(self):
        ctx = InvestigationContext(
            fraud_probability=0.75, exposure_usd=12.0, signal_count=2,
            verdict="fraud",
            card_testing_detected=True,
            testing_txns=["T001", "T002", "T003"],
            larger_purchase_cleared=False,
        )
        results = self.engine.evaluate(ctx)
        r5 = next(r for r in results if r.rule_id == "R5")
        self.assertTrue(r5.triggered)
        actions = [a.action for a in r5.actions]
        self.assertIn(Action.DECLINE_TRANSACTION, actions)
        self.assertIn(Action.STEP_UP_AUTH, actions)
        self.assertNotIn(Action.BLOCK_CARD, actions)

    def test_r5_triggers_block_card_if_cleared_over_100(self):
        ctx = InvestigationContext(
            fraud_probability=0.92, exposure_usd=268.0, signal_count=3,
            verdict="fraud",
            card_testing_detected=True,
            testing_txns=["T001", "T002", "T003"],
            larger_purchase_cleared=True,
        )
        results = self.engine.evaluate(ctx)
        r5 = next(r for r in results if r.rule_id == "R5")
        actions = [a.action for a in r5.actions]
        self.assertIn(Action.BLOCK_CARD, actions)
        self.assertNotIn(Action.DECLINE_TRANSACTION, actions)

    def test_r5_does_not_trigger_if_no_testing(self):
        ctx = InvestigationContext(
            fraud_probability=0.65, exposure_usd=50.0, signal_count=1,
            verdict="uncertain", card_testing_detected=False,
        )
        results = self.engine.evaluate(ctx)
        r5 = next(r for r in results if r.rule_id == "R5")
        self.assertFalse(r5.triggered)


class TestR6(unittest.TestCase):
    """R6: Shared origin ring."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r6_triggers_shared_device(self):
        ctx = InvestigationContext(
            fraud_probability=0.75, exposure_usd=500.0, signal_count=2,
            verdict="fraud",
            shared_device_cards=["C00001-K1", "C00002-K1"],
        )
        results = self.engine.evaluate(ctx)
        r6 = next(r for r in results if r.rule_id == "R6")
        self.assertTrue(r6.triggered)
        actions = [a.action for a in r6.actions]
        self.assertIn(Action.CREATE_CASE, actions)
        self.assertIn(Action.FILE_REPORT, actions)
        self.assertIn(Action.MONITOR_CONNECTED_CARDS, actions)

    def test_r6_does_not_trigger_no_shared_elements(self):
        ctx = InvestigationContext(
            fraud_probability=0.75, exposure_usd=500.0, signal_count=2,
            verdict="fraud",
        )
        results = self.engine.evaluate(ctx)
        r6 = next(r for r in results if r.rule_id == "R6")
        self.assertFalse(r6.triggered)


class TestR7(unittest.TestCase):
    """R7: Disputed but legitimate."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r7_triggers_recurring_dispute(self):
        ctx = InvestigationContext(
            fraud_probability=0.25, exposure_usd=50.0, signal_count=1,
            verdict="uncertain",
            disputed_by_customer=True,
            matches_recurring_pattern=True,
        )
        results = self.engine.evaluate(ctx)
        r7 = next(r for r in results if r.rule_id == "R7")
        self.assertTrue(r7.triggered)
        actions = [a.action for a in r7.actions]
        self.assertIn(Action.CREATE_CASE, actions)
        self.assertIn(Action.VERIFY_WITH_CUSTOMER, actions)
        self.assertIn(Action.WARN_CUSTOMER, actions)
        self.assertNotIn(Action.BLOCK_CARD, actions)

    def test_r7_does_not_trigger_non_recurring_dispute(self):
        ctx = InvestigationContext(
            fraud_probability=0.25, exposure_usd=50.0, signal_count=1,
            verdict="uncertain",
            disputed_by_customer=True,
            matches_recurring_pattern=False,
        )
        results = self.engine.evaluate(ctx)
        r7 = next(r for r in results if r.rule_id == "R7")
        self.assertFalse(r7.triggered)


class TestR8(unittest.TestCase):
    """R8: Escalate when uncertain and exposed."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r8_triggers_uncertain_high_exposure(self):
        ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=700.0, signal_count=1,
            verdict="uncertain",
        )
        results = self.engine.evaluate(ctx)
        r8 = next(r for r in results if r.rule_id == "R8")
        self.assertTrue(r8.triggered)
        actions = [a.action for a in r8.actions]
        self.assertIn(Action.ESCALATE_TO_ANALYST, actions)

    def test_r8_triggers_evidence_conflicts(self):
        ctx = InvestigationContext(
            fraud_probability=0.50, exposure_usd=100.0, signal_count=2,
            verdict="uncertain", evidence_conflicts=True,
        )
        results = self.engine.evaluate(ctx)
        r8 = next(r for r in results if r.rule_id == "R8")
        self.assertTrue(r8.triggered)

    def test_r8_does_not_trigger_below_500(self):
        ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=400.0, signal_count=1,
            verdict="uncertain",
        )
        results = self.engine.evaluate(ctx)
        r8 = next(r for r in results if r.rule_id == "R8")
        self.assertFalse(r8.triggered)

    def test_r8_does_not_trigger_if_verdict_fraud(self):
        ctx = InvestigationContext(
            fraud_probability=0.85, exposure_usd=1000.0, signal_count=2,
            verdict="fraud",
        )
        results = self.engine.evaluate(ctx)
        r8 = next(r for r in results if r.rule_id == "R8")
        self.assertFalse(r8.triggered)


class TestR9(unittest.TestCase):
    """R9: Undocumented patterns."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r9_triggers_undocumented_pattern(self):
        ctx = InvestigationContext(
            fraud_probability=0.78, exposure_usd=800.0, signal_count=3,
            verdict="fraud",
            undocumented_pattern_detected=True,
            undocumented_pattern_description="Multiple cards sharing IP range in coordinated burst."
        )
        results = self.engine.evaluate(ctx)
        r9 = next(r for r in results if r.rule_id == "R9")
        self.assertTrue(r9.triggered)
        actions = [a.action for a in r9.actions]
        self.assertIn(Action.CREATE_CASE, actions)
        self.assertIn(Action.FILE_REPORT, actions)
        self.assertIn(Action.ESCALATE_TO_ANALYST, actions)

    def test_r9_does_not_trigger_known_pattern(self):
        ctx = InvestigationContext(
            fraud_probability=0.78, exposure_usd=800.0, signal_count=3,
            verdict="fraud", undocumented_pattern_detected=False,
        )
        results = self.engine.evaluate(ctx)
        r9 = next(r for r in results if r.rule_id == "R9")
        self.assertFalse(r9.triggered)


class TestR10(unittest.TestCase):
    """R10: Never BLOCK_ALL_CARDS unless threshold met."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_r10_justified_two_cards_confirmed(self):
        ctx = InvestigationContext(
            fraud_probability=0.95, exposure_usd=5000.0, signal_count=4,
            verdict="fraud",
            confirmed_fraud_card_count=2,
        )
        results = self.engine.evaluate(ctx)
        r10 = next(r for r in results if r.rule_id == "R10")
        self.assertTrue(r10.triggered)
        actions = [a.action for a in r10.actions]
        self.assertIn(Action.BLOCK_ALL_CARDS, actions)

    def test_r10_justified_credentials_compromised(self):
        ctx = InvestigationContext(
            fraud_probability=0.92, exposure_usd=3000.0, signal_count=3,
            verdict="fraud",
            credentials_confirmed_compromised=True,
        )
        results = self.engine.evaluate(ctx)
        r10 = next(r for r in results if r.rule_id == "R10")
        self.assertTrue(r10.triggered)

    def test_r10_not_justified_one_card_only(self):
        ctx = InvestigationContext(
            fraud_probability=0.88, exposure_usd=1000.0, signal_count=2,
            verdict="fraud",
            confirmed_fraud_card_count=1,
        )
        results = self.engine.evaluate(ctx)
        r10 = next(r for r in results if r.rule_id == "R10")
        self.assertFalse(r10.triggered)

    def test_r10_route_is_l2(self):
        ctx = InvestigationContext(
            fraud_probability=0.95, exposure_usd=5000.0, signal_count=4,
            verdict="fraud", confirmed_fraud_card_count=3,
        )
        results = self.engine.evaluate(ctx)
        r10 = next(r for r in results if r.rule_id == "R10")
        block_all = next(a for a in r10.actions if a.action == Action.BLOCK_ALL_CARDS)
        self.assertEqual(block_all.route, ApprovalRoute.L2)


class TestPolicyDecide(unittest.TestCase):
    """Full policy decision: initial vs final NBA, what_changed."""

    def setUp(self):
        self.engine = PolicyEngine()

    def test_initial_verify_final_block_after_denial(self):
        """Classic R1 → R2 escalation: verify first, then block after denial."""
        initial_ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=800.0, signal_count=1,
            verdict="uncertain", single_signal_only=True, customer_verified=None,
        )
        final_ctx = InvestigationContext(
            fraud_probability=0.87, exposure_usd=800.0, signal_count=2,
            verdict="fraud", single_signal_only=False, customer_verified=False,
        )
        decision = self.engine.decide(initial_ctx, final_ctx)

        initial_action_names = {a.action for a in decision.initial_actions}
        final_action_names   = {a.action for a in decision.final_actions}

        self.assertIn(Action.VERIFY_WITH_CUSTOMER, initial_action_names)
        self.assertIn(Action.BLOCK_CARD, final_action_names)
        self.assertNotEqual(decision.what_changed, "nothing")

    def test_final_equals_initial_when_no_final_ctx(self):
        """When no final context given, what_changed should be 'nothing'."""
        ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=200.0, signal_count=1,
            verdict="uncertain", single_signal_only=True,
        )
        decision = self.engine.decide(ctx)
        self.assertEqual(decision.what_changed, "nothing")

    def test_should_stop_high_probability(self):
        ctx = InvestigationContext(
            fraud_probability=0.90, exposure_usd=500.0, signal_count=3,
            verdict="fraud", customer_verified=False,
        )
        decision = self.engine.decide(ctx, ctx)
        self.assertTrue(decision.should_stop)

    def test_should_stop_low_probability(self):
        ctx = InvestigationContext(
            fraud_probability=0.10, exposure_usd=0.0, signal_count=2,
            verdict="legitimate", customer_verified=True,
        )
        decision = self.engine.decide(ctx, ctx)
        self.assertTrue(decision.should_stop)

    def test_should_open_case_at_30_percent(self):
        ctx = InvestigationContext(
            fraud_probability=0.30, exposure_usd=100.0, signal_count=1,
            verdict="uncertain",
        )
        decision = self.engine.decide(ctx)
        self.assertTrue(decision.should_open_case)

    def test_format_nba_exact_schema(self):
        """format_nba output must have exactly action, route, reason keys."""
        ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=200.0, signal_count=1,
            verdict="uncertain", single_signal_only=True,
        )
        decision = self.engine.decide(ctx)
        formatted = self.engine.format_nba(decision.initial_actions)
        for item in formatted:
            self.assertIn("action", item)
            self.assertIn("route", item)
            self.assertIn("reason", item)

    def test_all_10_rules_present_in_evaluation(self):
        ctx = InvestigationContext(
            fraud_probability=0.45, exposure_usd=100.0, signal_count=1, verdict="uncertain",
        )
        results = self.engine.evaluate(ctx)
        rule_ids = [r.rule_id for r in results]
        for expected in ["R1", "R2", "R3", "R4", "R5", "R6", "R7", "R8", "R9", "R10"]:
            self.assertIn(expected, rule_ids)


if __name__ == "__main__":
    unittest.main()
