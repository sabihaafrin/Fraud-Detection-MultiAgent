"""Loads the demo data from data/customers.csv and data/transactions.csv.

The CSVs are synthetic (see scripts/generate_data.py) and include the three
hand-picked demo transactions as T1001-T1003, one per decision bucket:
T1001 clean -> approve, T1002 egregious -> decline, T1003 borderline -> review.

The `scenario` and `is_fraud` columns are ground-truth labels for evaluation.
They are split off into LABELS so the agents (and the LLM prompts, which see
the whole transaction) never get a peek at the answer.

Swap this module for a different loader (e.g. a real dataset) when you want —
nothing else in the system needs to change, as long as it produces the same
fields.
"""

import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

LABEL_FIELDS = ("scenario", "is_fraud")


def _bool(value: str) -> bool:
    return value.strip().lower() == "true"


def _load_customers() -> dict[str, dict]:
    with open(DATA_DIR / "customers.csv", newline="", encoding="utf-8") as f:
        return {
            row["customer_id"]: {
                "home_country": row["home_country"],
                "typical_amount_gbp": float(row["typical_amount_gbp"]),
                "max_normal_amount_gbp": float(row["max_normal_amount_gbp"]),
                "usual_categories": row["usual_categories"].split("|"),
                "usual_hours": row["usual_hours"],
                "known_devices": row["known_devices"].split("|"),
            }
            for row in csv.DictReader(f)
        }


def _load_transactions() -> tuple[list[dict], dict[str, dict]]:
    transactions, labels = [], {}
    with open(DATA_DIR / "transactions.csv", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            transactions.append({
                "id": row["id"],
                "customer_id": row["customer_id"],
                "amount_gbp": float(row["amount_gbp"]),
                "country": row["country"],
                "category": row["category"],
                "hour": int(row["hour"]),
                "device_id": row["device_id"],
                "txns_last_hour": int(row["txns_last_hour"]),
                "new_payee": _bool(row["new_payee"]),
                "minutes_since_last_txn": int(row["minutes_since_last_txn"]),
                "last_txn_country": row["last_txn_country"],
            })
            labels[row["id"]] = {
                "scenario": row["scenario"],
                "is_fraud": _bool(row["is_fraud"]),
            }
    return transactions, labels


# One entry per customer: what "normal" looks like for them.
CUSTOMER_HISTORY = _load_customers()

# Every transaction, without labels. The first three are the classic demo.
SAMPLE_TRANSACTIONS, LABELS = _load_transactions()
DEMO_TRANSACTIONS = SAMPLE_TRANSACTIONS[:3]
