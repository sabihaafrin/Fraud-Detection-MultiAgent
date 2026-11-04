"""Orchestrator — the entry node.

In a LangGraph system the *routing* is the graph itself (see graph.py). This
node does the orchestrator's setup job: it looks up the customer's history and
attaches it to the state so the downstream specialists have what they need.
"""

from ..sample_data import CUSTOMER_HISTORY
from ..state import FraudState


def orchestrator_node(state: FraudState) -> dict:
    txn = state["transaction"]
    history = CUSTOMER_HISTORY.get(txn["customer_id"], {})
    print(f"\n{'=' * 60}\n[Orchestrator] Received {txn['id']} "
          f"(customer {txn['customer_id']}, £{txn['amount_gbp']:,.2f})")
    return {"customer_history": history}
