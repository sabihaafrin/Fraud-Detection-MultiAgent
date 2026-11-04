"""Measure how well the system's decisions match the ground-truth labels.

Every score and routing decision is computed in Python — the LLM only writes
explanations — so this runs the same decision functions the agents use,
without the LLM or the console pause. All 120 transactions take about a second.

Cases routed to "review" go to a human, so they are counted separately: a
fraud sent to review is caught (a human sees it), but it costs analyst time.

Run from the project root:
    python -m src.evaluate            # summary
    python -m src.evaluate --details  # also list every misclassified case
"""

import argparse
import csv
from collections import Counter
from pathlib import Path

from .agents.adjudicator import adjudicate
from .agents.behavioural import evaluate_behaviour
from .agents.rules import evaluate_rules
from .sample_data import CUSTOMER_HISTORY, LABELS, SAMPLE_TRANSACTIONS

RESULTS_PATH = Path(__file__).resolve().parent.parent / "results" / "evaluation.csv"
ACTIONS = ("approve", "review", "decline")


def decide(txn: dict) -> dict:
    """Run one transaction through the same scoring the graph uses."""
    rule_flags, rule_risk = evaluate_rules(txn)
    behavioural_flags, behavioural_risk = evaluate_behaviour(
        txn, CUSTOMER_HISTORY.get(txn["customer_id"], {}))
    score, action = adjudicate(rule_risk, behavioural_risk)
    return {
        "id": txn["id"],
        "customer_id": txn["customer_id"],
        "amount_gbp": txn["amount_gbp"],
        "rule_flags": "|".join(rule_flags),
        "rule_risk": rule_risk,
        "behavioural_flags": "|".join(behavioural_flags),
        "behavioural_risk": behavioural_risk,
        "risk_score": score,
        "action": action,
        **LABELS[txn["id"]],
    }


def _pct(part: int, whole: int) -> str:
    return f"{100 * part / whole:5.1f}%" if whole else "    -"


def print_report(results: list[dict]) -> None:
    by_truth = Counter((r["is_fraud"], r["action"]) for r in results)
    frauds = sum(1 for r in results if r["is_fraud"])
    legit = len(results) - frauds

    print(f"\nEvaluated {len(results)} transactions ({frauds} fraud, {legit} legitimate)\n")

    print("Outcome by ground truth")
    print(f"  {'':12}{'approve':>10}{'review':>10}{'decline':>10}{'total':>8}")
    for label, is_fraud, total in (("fraud", True, frauds), ("legitimate", False, legit)):
        cells = "".join(f"{by_truth[(is_fraud, a)]:>10}" for a in ACTIONS)
        print(f"  {label:12}{cells}{total:>8}")

    caught_auto = by_truth[(True, "decline")]
    caught_human = by_truth[(True, "review")]
    missed = by_truth[(True, "approve")]
    false_declines = by_truth[(False, "decline")]
    legit_reviewed = by_truth[(False, "review")]
    reviews = caught_human + legit_reviewed

    print("\nFraud")
    print(f"  Auto-declined         {caught_auto:>4}  {_pct(caught_auto, frauds)}")
    print(f"  Sent to a human       {caught_human:>4}  {_pct(caught_human, frauds)}")
    print(f"  Missed (approved)     {missed:>4}  {_pct(missed, frauds)}")
    print(f"  Detection rate        {caught_auto + caught_human:>4}  "
          f"{_pct(caught_auto + caught_human, frauds)}   (declined or reviewed)")

    print("\nLegitimate customers")
    print(f"  Wrongly declined      {false_declines:>4}  {_pct(false_declines, legit)}")
    print(f"  Sent to a human       {legit_reviewed:>4}  {_pct(legit_reviewed, legit)}")

    print("\nHuman workload")
    print(f"  Cases needing review  {reviews:>4}  {_pct(reviews, len(results))} of all traffic")
    print(f"  ...of which fraud     {caught_human:>4}  {_pct(caught_human, reviews)}")

    print("\nBy scenario")
    by_scenario = Counter((r["scenario"], r["action"]) for r in results)
    for scenario in ("clean", "borderline", "fraud"):
        cells = "  ".join(f"{a} {by_scenario[(scenario, a)]:>3}" for a in ACTIONS)
        print(f"  {scenario:12}{cells}")


def print_details(results: list[dict]) -> None:
    wrong = [r for r in results
             if (r["is_fraud"] and r["action"] == "approve")
             or (not r["is_fraud"] and r["action"] == "decline")]
    print(f"\nMisclassified ({len(wrong)}): fraud approved, or legitimate declined")
    for r in wrong:
        kind = "MISSED FRAUD " if r["is_fraud"] else "FALSE DECLINE"
        print(f"  {kind} {r['id']}  £{r['amount_gbp']:>9,.2f}  score={r['risk_score']:>3}  "
              f"rules=[{r['rule_flags'] or '-'}]  behaviour=[{r['behavioural_flags'] or '-'}]")


def main():
    parser = argparse.ArgumentParser(description="Evaluate decisions against ground truth.")
    parser.add_argument("--details", action="store_true", help="list misclassified cases")
    args = parser.parse_args()

    results = [decide(txn) for txn in SAMPLE_TRANSACTIONS]
    print_report(results)
    if args.details:
        print_details(results)

    RESULTS_PATH.parent.mkdir(exist_ok=True)
    with open(RESULTS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    print(f"\nPer-transaction results written to {RESULTS_PATH}")


if __name__ == "__main__":
    main()
