"""Tools: the lookups and checks the system exposes, as LangChain tools.

The Orchestrator retrieves customer history through `get_customer_profile`,
and the same tools are served over MCP (see mcp_server.py) so other agents —
Claude Desktop, an IDE assistant, another LangGraph app — can call the fraud
checks directly. All tools are read-only: none can approve or decline a
payment, which stays behind the human checkpoint.
"""

from langchain_core.tools import tool

from .agents.adjudicator import adjudicate
from .agents.behavioural import evaluate_behaviour
from .agents.rules import evaluate_rules
from .models import validate_transaction
from .sample_data import CUSTOMER_HISTORY


@tool
def get_customer_profile(customer_id: str) -> dict:
    """Return a customer's normal behaviour: home country, typical and maximum
    amounts, usual categories, usual hours and known devices. Empty if unknown."""
    return CUSTOMER_HISTORY.get(customer_id, {})


@tool
def score_transaction(transaction: dict) -> dict:
    """Score a transaction with the deterministic Rules and Behavioural checks.

    Returns the triggered rule flags, behavioural signals, each agent's risk,
    the overall 0-100 risk score and the recommended action
    (approve | review | decline). Does not call the LLM and does not act on
    the payment."""
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
