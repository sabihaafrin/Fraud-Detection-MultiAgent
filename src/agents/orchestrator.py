import logging

from ..models import validate_transaction
from ..observability import traced
from ..state import FraudState
from ..tools import get_customer_profile

log = logging.getLogger(__name__)


@traced("orchestrator")
def orchestrator_node(state: FraudState) -> dict:
    txn = validate_transaction(state["transaction"])
    history = get_customer_profile.invoke({"customer_id": txn["customer_id"]})
    log.info(f"\n{'=' * 60}\n[Orchestrator] Received {txn['id']} "
             f"(customer {txn['customer_id']}, £{txn['amount_gbp']:,.2f})"
             + ("" if history else "  (no history on file)"))
    return {"transaction": txn, "customer_history": history}
