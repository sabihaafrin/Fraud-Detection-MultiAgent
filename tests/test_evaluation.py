"""Regression gate on accuracy against the labelled dataset.

If a change to the rules, weights or thresholds makes the system worse than
these bars, the test (and CI) fails. Tighten them as the system improves.
"""

import asyncio

from src.evaluate import metrics, misclassified, run_evaluation
from src.sample_data import LABELS, SAMPLE_TRANSACTIONS


def test_labels_cover_every_transaction_and_never_reach_agents():
    assert set(LABELS) == {t["id"] for t in SAMPLE_TRANSACTIONS}
    assert all("is_fraud" not in t and "scenario" not in t for t in SAMPLE_TRANSACTIONS)


def test_demo_transactions_land_in_their_buckets():
    actions = {r["id"]: r["action"] for r in run_evaluation()[:3]}
    assert actions == {"T1001": "approve", "T1002": "decline", "T1003": "review"}


def test_accuracy_meets_minimum_bars():
    m = metrics(run_evaluation())
    assert m["detection_rate"] >= 0.85        # currently 87%
    assert m["false_decline_rate"] == 0.0     # no genuine customer auto-declined
    assert m["review_rate"] <= 0.15           # human workload stays manageable


def test_every_obvious_fraud_is_declined_and_every_clean_approved():
    results = run_evaluation()
    assert all(r["action"] == "decline" for r in results if r["scenario"] == "fraud")
    assert all(r["action"] == "approve" for r in results if r["scenario"] == "clean")


def test_known_misses_are_low_value_single_signal_cases():
    """Documents the known limitation (see docs/EVALUATION.md)."""
    for r in misclassified(run_evaluation()):
        assert r["is_fraud"] and r["rule_flags"] == ""
        assert r["behavioural_flags"] == "unusual_category"


def test_mcp_server_exposes_read_only_tools():
    from src.mcp_server import server
    names = {t.name for t in asyncio.run(server.list_tools())}
    assert names == {"score_transaction", "get_customer_profile", "evaluation_summary"}
