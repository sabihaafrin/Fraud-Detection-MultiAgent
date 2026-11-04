"""Measure how well the system's decisions match the ground-truth labels.

Every score and routing decision is computed in Python — the LLM only writes
explanations — so this runs the same decision functions the agents use,
without the LLM or the console pause. All 120 transactions take about a second.

Cases routed to "review" go to a human, so they are counted separately: a
fraud sent to review is caught (a human sees it), but it costs analyst time.

Run from the project root:
    python -m src.evaluate            # summary
    python -m src.evaluate --details  # also list every misclassified case

Writes results/evaluation.csv (per transaction) and
results/evaluation_report.md (the summary, committed as evidence).
"""

import argparse
import csv
from collections import Counter
from datetime import date
from pathlib import Path

from . import config
from .agents.adjudicator import adjudicate
from .agents.behavioural import evaluate_behaviour
from .agents.rules import evaluate_rules
from .sample_data import CUSTOMER_HISTORY, LABELS, SAMPLE_TRANSACTIONS

RESULTS_DIR = Path(__file__).resolve().parent.parent / "results"
ACTIONS = ("approve", "review", "decline")


def decide(txn: dict, approve_below: int | None = None,
           decline_at_or_above: int | None = None) -> dict:
    """Run one transaction through the same scoring the graph uses."""
    rule_flags, rule_risk = evaluate_rules(txn)
    behavioural_flags, behavioural_risk = evaluate_behaviour(
        txn, CUSTOMER_HISTORY.get(txn["customer_id"], {}))
    score, action = adjudicate(rule_risk, behavioural_risk, approve_below, decline_at_or_above)
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


def run_evaluation(approve_below: int | None = None,
                   decline_at_or_above: int | None = None) -> list[dict]:
    return [decide(txn, approve_below, decline_at_or_above) for txn in SAMPLE_TRANSACTIONS]


def metrics(results: list[dict]) -> dict:
    """Headline numbers. Rates are fractions (0-1)."""
    counts = Counter((r["is_fraud"], r["action"]) for r in results)
    frauds = sum(1 for r in results if r["is_fraud"])
    legit = len(results) - frauds
    reviews = counts[(True, "review")] + counts[(False, "review")]

    def rate(part, whole):
        return part / whole if whole else 0.0

    return {
        "transactions": len(results),
        "frauds": frauds,
        "legitimate": legit,
        "counts": {f"{'fraud' if f else 'legitimate'}_{a}": counts[(f, a)]
                   for f in (True, False) for a in ACTIONS},
        "detection_rate": rate(counts[(True, "decline")] + counts[(True, "review")], frauds),
        "auto_decline_rate": rate(counts[(True, "decline")], frauds),
        "missed_fraud_rate": rate(counts[(True, "approve")], frauds),
        "false_decline_rate": rate(counts[(False, "decline")], legit),
        "review_rate": rate(reviews, len(results)),
        "review_precision": rate(counts[(True, "review")], reviews),
    }


def misclassified(results: list[dict]) -> list[dict]:
    return [r for r in results
            if (r["is_fraud"] and r["action"] == "approve")
            or (not r["is_fraud"] and r["action"] == "decline")]


def _pct(x: float) -> str:
    return f"{100 * x:5.1f}%"


def print_report(results: list[dict]) -> None:
    m, c = metrics(results), metrics(results)["counts"]
    print(f"\nEvaluated {m['transactions']} transactions "
          f"({m['frauds']} fraud, {m['legitimate']} legitimate)\n")

    print("Outcome by ground truth")
    print(f"  {'':12}{'approve':>10}{'review':>10}{'decline':>10}{'total':>8}")
    for label, total in (("fraud", m["frauds"]), ("legitimate", m["legitimate"])):
        cells = "".join(f"{c[f'{label}_{a}']:>10}" for a in ACTIONS)
        print(f"  {label:12}{cells}{total:>8}")

    print("\nFraud")
    print(f"  Auto-declined         {c['fraud_decline']:>4}  {_pct(m['auto_decline_rate'])}")
    print(f"  Sent to a human       {c['fraud_review']:>4}")
    print(f"  Missed (approved)     {c['fraud_approve']:>4}  {_pct(m['missed_fraud_rate'])}")
    print(f"  Detection rate              {_pct(m['detection_rate'])}   (declined or reviewed)")

    print("\nLegitimate customers")
    print(f"  Wrongly declined      {c['legitimate_decline']:>4}  {_pct(m['false_decline_rate'])}")
    print(f"  Sent to a human       {c['legitimate_review']:>4}")

    print("\nHuman workload")
    print(f"  Review rate                 {_pct(m['review_rate'])} of all traffic")
    print(f"  ...of which fraud           {_pct(m['review_precision'])}")

    print("\nBy scenario")
    by_scenario = Counter((r["scenario"], r["action"]) for r in results)
    for scenario in ("clean", "borderline", "fraud"):
        cells = "  ".join(f"{a} {by_scenario[(scenario, a)]:>3}" for a in ACTIONS)
        print(f"  {scenario:12}{cells}")


def print_details(results: list[dict]) -> None:
    wrong = misclassified(results)
    print(f"\nMisclassified ({len(wrong)}): fraud approved, or legitimate declined")
    for r in wrong:
        kind = "MISSED FRAUD " if r["is_fraud"] else "FALSE DECLINE"
        print(f"  {kind} {r['id']}  £{r['amount_gbp']:>9,.2f}  score={r['risk_score']:>3}  "
              f"rules=[{r['rule_flags'] or '-'}]  behaviour=[{r['behavioural_flags'] or '-'}]")


def write_markdown(results: list[dict], path: Path) -> None:
    m, c = metrics(results), metrics(results)["counts"]
    wrong = misclassified(results)
    lines = [
        "# Evaluation report",
        "",
        f"*Generated by `python -m src.evaluate` on {date.today().isoformat()} — "
        f"thresholds: approve < {config.APPROVE_BELOW}, "
        f"decline >= {config.DECLINE_AT_OR_ABOVE}.*",
        "",
        f"Dataset: `data/transactions.csv` — {m['transactions']} synthetic transactions "
        f"({m['frauds']} fraud, {m['legitimate']} legitimate).",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Fraud detection rate (declined or reviewed) | {_pct(m['detection_rate']).strip()} |",
        f"| Fraud auto-declined | {_pct(m['auto_decline_rate']).strip()} |",
        f"| Fraud missed (approved) | {_pct(m['missed_fraud_rate']).strip()} |",
        f"| Legitimate customers wrongly declined | {_pct(m['false_decline_rate']).strip()} |",
        f"| Share of traffic sent to a human | {_pct(m['review_rate']).strip()} |",
        f"| Share of reviews that were fraud | {_pct(m['review_precision']).strip()} |",
        "",
        "| Ground truth | approve | review | decline |",
        "|---|---|---|---|",
        f"| fraud | {c['fraud_approve']} | {c['fraud_review']} | {c['fraud_decline']} |",
        f"| legitimate | {c['legitimate_approve']} | {c['legitimate_review']} "
        f"| {c['legitimate_decline']} |",
        "",
        f"## Misclassified ({len(wrong)})",
        "",
    ]
    if wrong:
        lines += ["| Transaction | Truth | Action | Score | Rule flags | Behavioural signals |",
                  "|---|---|---|---|---|---|"]
        lines += [f"| {r['id']} | {'fraud' if r['is_fraud'] else 'legitimate'} | {r['action']} "
                  f"| {r['risk_score']} | {r['rule_flags'] or '-'} "
                  f"| {r['behavioural_flags'] or '-'} |" for r in wrong]
    else:
        lines.append("None.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Evaluate decisions against ground truth.")
    parser.add_argument("--details", action="store_true", help="list misclassified cases")
    args = parser.parse_args()

    results = run_evaluation()
    print_report(results)
    if args.details:
        print_details(results)

    RESULTS_DIR.mkdir(exist_ok=True)
    with open(RESULTS_DIR / "evaluation.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    write_markdown(results, RESULTS_DIR / "evaluation_report.md")
    print(f"\nResults written to {RESULTS_DIR / 'evaluation.csv'} "
          f"and {RESULTS_DIR / 'evaluation_report.md'}")


if __name__ == "__main__":
    main()
