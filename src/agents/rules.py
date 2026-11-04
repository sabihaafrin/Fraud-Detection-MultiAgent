"""Rules agent — deterministic and fully explainable.

No LLM here: hard rules should be fast and auditable. Each triggered rule adds
a fixed amount to this agent's risk contribution. The Adjudicator weighs this
against the Behavioural agent's view.
"""

from .. import config
from ..state import FraudState


def evaluate_rules(txn: dict) -> tuple[list[str], int]:
    """Return the triggered rule flags and this agent's risk (0-100)."""
    flags: list[str] = []
    risk = 0

    if txn["amount_gbp"] > config.HIGH_AMOUNT_GBP:
        flags.append("high_amount")
        risk += 30

    if txn["txns_last_hour"] > config.MAX_TXNS_PER_HOUR:
        flags.append("high_velocity")
        risk += 20

    if (txn["country"] != txn["last_txn_country"]
            and txn["minutes_since_last_txn"] < config.IMPOSSIBLE_TRAVEL_MINUTES):
        flags.append("impossible_travel")
        risk += 25

    if txn["device_id"] in config.BLOCKLISTED_DEVICES:
        flags.append("blocklisted_device")
        risk += 40

    if txn["new_payee"] and txn["amount_gbp"] > config.NEW_PAYEE_AMOUNT_GBP:
        flags.append("new_payee_high_amount")
        risk += 10

    return flags, min(risk, 100)


def rules_node(state: FraudState) -> dict:
    flags, risk = evaluate_rules(state["transaction"])
    print(f"[Rules]        flags={flags or 'none'}  risk={risk}")
    return {"rule_flags": flags, "rule_risk": risk}
