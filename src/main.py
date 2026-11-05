import argparse
import getpass
import logging
import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from .graph import build_graph
from .models import InvalidTransaction
from .observability import setup_logging
from .sample_data import SAMPLE_TRANSACTIONS

log = logging.getLogger(__name__)


def ask_human(payload: dict) -> dict:
    print("\n  ----- HUMAN REVIEW REQUIRED -----")
    print(f"  Transaction : {payload['transaction']['id']} "
          f"(£{payload['transaction']['amount_gbp']:,.2f})")
    print(f"  Risk score  : {payload['risk_score']}/100")
    print(f"  Rule flags  : {payload['rule_flags'] or 'none'}")
    print(f"  Rationale   : {payload['rationale']}")
    while True:
        verdict = input("  Your decision [approve/decline]: ").strip().lower()
        if verdict in ("approve", "decline"):
            note = input("  Reason (optional): ").strip()
            return {"decision": verdict, "reviewer": getpass.getuser(), "note": note}
        print("  Please type 'approve' or 'decline'.")


def run_one(graph, txn: dict) -> dict:
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"transaction": txn}, config=config)

    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        verdict = ask_human(payload)
        result = graph.invoke(Command(resume=verdict), config=config)

    return result


def main():
    parser = argparse.ArgumentParser(description="Run transactions through the fraud graph.")
    parser.add_argument("--limit", type=int, default=3,
                        help="number of transactions to run (default: 3, the demo set)")
    parser.add_argument("--all", action="store_true", help="run every transaction")
    args = parser.parse_args()
    transactions = SAMPLE_TRANSACTIONS if args.all else SAMPLE_TRANSACTIONS[:args.limit]

    load_dotenv()
    setup_logging()
    graph = build_graph()

    outcomes = []
    for txn in transactions:
        try:
            result = run_one(graph, txn)
        except InvalidTransaction as e:
            log.error(f"[Rejected]     {txn.get('id', '?')}: {e}")
            continue
        reviewer = "human" if result.get("human_reviewed") else "auto"
        outcomes.append((txn["id"], result["final_action"], reviewer))
        print(f"[Outcome]      {txn['id']} -> {result['final_action'].upper()} ({reviewer})")

    print(f"\n{'=' * 60}\nSUMMARY")
    for txn_id, action, reviewer in outcomes:
        print(f"  {txn_id}: {action.upper():8} ({reviewer})")


if __name__ == "__main__":
    main()
