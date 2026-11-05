import pytest

from src.agents.adjudicator import adjudicate
from src.agents.behavioural import _within_hours, evaluate_behaviour
from src.agents.rules import evaluate_rules
from src.sample_data import CUSTOMER_HISTORY

CLEAN = dict(id="T9001", customer_id="C001", amount_gbp=40.0, country="GB",
             category="groceries", hour=12, device_id="device_a1", txns_last_hour=1,
             new_payee=False, minutes_since_last_txn=300, last_txn_country="GB")


def test_clean_transaction_triggers_no_rules():
    assert evaluate_rules(CLEAN) == ([], 0)


@pytest.mark.parametrize("change, flag, risk", [
    ({"amount_gbp": 6000}, "high_amount", 30),
    ({"txns_last_hour": 6}, "high_velocity", 20),
    ({"country": "NG", "minutes_since_last_txn": 10}, "impossible_travel", 25),
    ({"device_id": "device_bad_99"}, "blocklisted_device", 40),
    ({"new_payee": True, "amount_gbp": 600}, "new_payee_high_amount", 10),
])
def test_each_rule_fires_alone(change, flag, risk):
    assert evaluate_rules({**CLEAN, **change}) == ([flag], risk)


def test_travel_with_enough_time_is_not_impossible():
    flags, _ = evaluate_rules({**CLEAN, "country": "FR", "minutes_since_last_txn": 600})
    assert "impossible_travel" not in flags


def test_rules_risk_is_capped_at_100():
    txn = {**CLEAN, "amount_gbp": 9000, "txns_last_hour": 9, "country": "NG",
           "minutes_since_last_txn": 5, "device_id": "device_bad_99", "new_payee": True}
    flags, risk = evaluate_rules(txn)
    assert len(flags) == 5 and risk == 100


def test_clean_transaction_fits_behaviour():
    assert evaluate_behaviour(CLEAN, CUSTOMER_HISTORY["C001"]) == ([], 0)


def test_behavioural_signals_and_weights():
    txn = {**CLEAN, "amount_gbp": 500, "hour": 2}   # C001 max is 400, hours 07-22
    signals, risk = evaluate_behaviour(txn, CUSTOMER_HISTORY["C001"])
    assert signals == ["above_normal_maximum", "outside_usual_hours"]
    assert risk == 50


def test_unknown_customer_has_no_behavioural_signals():
    assert evaluate_behaviour(CLEAN, {}) == ([], 0)


@pytest.mark.parametrize("hour, window, expected", [
    (7, "07:00-22:00", True),
    (22, "07:00-22:00", False),   # end hour is exclusive
    (2, "07:00-22:00", False),
    (23, "20:00-06:00", True),    # window wrapping midnight
    (3, "20:00-06:00", True),
    (12, "20:00-06:00", False),
])
def test_within_hours(hour, window, expected):
    assert _within_hours(hour, window) is expected


@pytest.mark.parametrize("rule_risk, behavioural_risk, expected", [
    (0, 0, (0, "approve")),
    (20, 14, (34, "approve")),
    (20, 15, (35, "review")),     # APPROVE_BELOW = 35
    (40, 34, (74, "review")),
    (40, 35, (75, "decline")),    # DECLINE_AT_OR_ABOVE = 75
    (100, 85, (100, "decline")),  # capped at 100
])
def test_adjudicate_thresholds(rule_risk, behavioural_risk, expected):
    assert adjudicate(rule_risk, behavioural_risk) == expected


def test_adjudicate_accepts_what_if_thresholds():
    assert adjudicate(10, 10, approve_below=15) == (20, "review")
