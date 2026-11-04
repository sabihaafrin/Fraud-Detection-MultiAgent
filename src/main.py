"""Run the demo: push each sample transaction through the graph.

For borderline cases the graph interrupts; we print the case file, ask the
human on the console, then resume the graph with their verdict.

Run from the project root:   python -m src.main
"""

import uuid

from dotenv import load_dotenv
from langgraph.types import Command

from .graph import build_graph
from .sample_data import SAMPLE_TRANSACTIONS


def ask_human(payload: dict) -> str:
    """Show the case file and get an approve/decline verdict."""
    print("\n  ----- HUMAN REVIEW REQUIRED -----")
    print(f"  Transaction : {payload['transaction']['id']} "
          f"(£{payload['transaction']['amount_gbp']:,.2f})")
    print(f"  Risk score  : {payload['risk_score']}/100")
    print(f"  Rule flags  : {payload['rule_flags'] or 'none'}")
    print(f"  Rationale   : {payload['rationale']}")
    while True:
        verdict = input("  Your decision [approve/decline]: ").strip().lower()
        if verdict in ("approve", "decline"):
            return verdict
        print("  Please type 'approve' or 'decline'.")


def run_one(graph, txn: dict) -> dict:
    # A unique thread_id per transaction keeps each run's checkpoint separate.
    config = {"configurable": {"thread_id": str(uuid.uuid4())}}
    result = graph.invoke({"transaction": txn}, config=config)

    # If the graph paused at human_review, result carries an interrupt.
    if "__interrupt__" in result:
        payload = result["__interrupt__"][0].value
        verdict = ask_human(payload)
        result = graph.invoke(Command(resume=verdict), config=config)

    return result


def main():
    load_dotenv()
    graph = build_graph()

    outcomes = []
    for txn in SAMPLE_TRANSACTIONS:
        result = run_one(graph, txn)
        reviewer = "human" if result.get("human_reviewed") else "auto"
        outcomes.append((txn["id"], result["final_action"], reviewer))
        print(f"[Outcome]      {txn['id']} -> {result['final_action'].upper()} ({reviewer})")

    print(f"\n{'=' * 60}\nSUMMARY")
    for txn_id, action, reviewer in outcomes:
        print(f"  {txn_id}: {action.upper():8} ({reviewer})")


if __name__ == "__main__":
    main()
