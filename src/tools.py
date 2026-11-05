from langchain_core.tools import tool

from .agents.adjudicator import adjudicate
from .agents.behavioural import evaluate_behaviour
from .agents.rules import evaluate_rules
from .models import validate_transaction
from .sample_data import CUSTOMER_HISTORY


@tool
def get_customer_profile(customer_id: str) -> dict:
    """Return a customer's normal behaviour, or an empty dict if unknown."""
    return CUSTOMER_HISTORY.get(customer_id, {})


@tool
def score_transaction(transaction: dict) -> dict:
    """Score a transaction with the rules and behavioural checks (no LLM)."""
    txn = validate_transaction(transaction)
    rule_flags, rule_risk = evaluate_rules(txn)
    behavioural_flags, behavioural_risk = evaluate_behaviour(
        txn, CUSTOMER_HISTORY.get(txn["customer_id"], {}))
    score, action = adjudicate(rule_risk, behavioural_risk)
    return {
        "transaction_id": txn["id"],
        "rule_flags": rule_flags,
        "rule_risk": rule_risk,
        "behavioural_flags": behavioural_flags,
        "behavioural_risk": behavioural_risk,
        "risk_score": score,
        "recommended_action": action,
    }
