import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


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


# The scenario and is_fraud columns are kept separate so the agents never see them.
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


CUSTOMER_HISTORY = _load_customers()
SAMPLE_TRANSACTIONS, LABELS = _load_transactions()
