"""
Each transaction is generated from one of three scenarios:
  clean       fits the customer's normal behaviour, no hard-rule triggers
  fraud       several strong signals (blocklisted/unknown device, impossible
              travel, velocity, huge amount, unusual category, night-time)
  borderline  one or two out-of-character signals, no damning rule hit —
              some are real fraud, most are the customer doing something new

`scenario` and `is_fraud` are labels for evaluation only — sample_data.py
keeps them away from the agents.

Run from the project root:   python scripts/generate_data.py
"""

import csv
import random
from pathlib import Path

SEED = 42
N_CLEAN = 80
N_FRAUD = 17
N_BORDERLINE = 20
BORDERLINE_FRAUD_RATE = 0.3

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

CATEGORIES = ["groceries", "transport", "dining", "electronics", "travel",
              "fashion", "utilities", "entertainment", "health"]
RISKY_CATEGORIES = ["crypto", "gift_cards", "electronics", "money_transfer"]
FOREIGN_COUNTRIES = ["NG", "RU", "BR", "CN", "RO", "US", "AE", "IN"]
BLOCKLISTED = ["device_unknown_x", "device_bad_99"]

# The two customers from the original hand-written demo, kept unchanged.
CUSTOMERS = {
    "C001": dict(home_country="GB", typical_amount_gbp=60, max_normal_amount_gbp=400,
                 usual_categories=["groceries", "transport", "dining"],
                 usual_hours="07:00-22:00", known_devices=["device_a1"]),
    "C002": dict(home_country="FR", typical_amount_gbp=120, max_normal_amount_gbp=900,
                 usual_categories=["electronics", "travel", "dining"],
                 usual_hours="08:00-23:00", known_devices=["device_b2"]),
}

# The three demo transactions — one per decision bucket — stay as T1001-T1003.
DEMO_TRANSACTIONS = [
    dict(id="T1001", customer_id="C001", amount_gbp=42.50, country="GB",
         category="groceries", hour=18, device_id="device_a1", txns_last_hour=1,
         new_payee=False, minutes_since_last_txn=240, last_txn_country="GB",
         scenario="clean", is_fraud=False),
    dict(id="T1002", customer_id="C001", amount_gbp=8800.00, country="NG",
         category="crypto", hour=3, device_id="device_unknown_x", txns_last_hour=9,
         new_payee=True, minutes_since_last_txn=12, last_txn_country="GB",
         scenario="fraud", is_fraud=True),
    dict(id="T1003", customer_id="C002", amount_gbp=1400.00, country="FR",
         category="electronics", hour=2, device_id="device_b2", txns_last_hour=2,
         new_payee=True, minutes_since_last_txn=180, last_txn_country="FR",
         scenario="borderline", is_fraud=False),
]

NEW_CUSTOMER_PROFILES = [
    # (home_country, typical, max_normal, usual_hours)
    ("GB", 45, 300, "07:00-21:00"),
    ("GB", 150, 1200, "08:00-23:00"),
    ("DE", 80, 600, "06:00-20:00"),
    ("ES", 35, 250, "09:00-23:00"),
    ("IE", 200, 1500, "07:00-22:00"),
    ("GB", 25, 150, "10:00-22:00"),
    ("NL", 95, 700, "07:00-23:00"),
    ("IT", 60, 450, "08:00-22:00"),
    ("FR", 300, 2500, "06:00-22:00"),
    ("GB", 70, 500, "07:00-20:00"),
]


def _hours(usual_hours: str) -> tuple[int, int]:
    start, end = (int(part.split(":")[0]) for part in usual_hours.split("-"))
    return start, end


def make_customers(rng: random.Random) -> dict:
    customers = dict(CUSTOMERS)
    for i, (country, typical, max_normal, hours) in enumerate(NEW_CUSTOMER_PROFILES, start=3):
        cid = f"C{i:03d}"
        customers[cid] = dict(
            home_country=country,
            typical_amount_gbp=typical,
            max_normal_amount_gbp=max_normal,
            usual_categories=rng.sample(CATEGORIES, 3),
            usual_hours=hours,
            known_devices=[f"device_{cid.lower()}_{n}" for n in range(rng.randint(1, 2))],
        )
    return customers


def clean_txn(rng, cid, c) -> dict:
    start, end = _hours(c["usual_hours"])
    amount = min(rng.lognormvariate(0, 0.6) * c["typical_amount_gbp"],
                 c["max_normal_amount_gbp"] * 0.9)
    return dict(
        customer_id=cid,
        amount_gbp=round(amount, 2),
        country=c["home_country"],
        category=rng.choice(c["usual_categories"]),
        hour=rng.randint(start, end - 1),
        device_id=rng.choice(c["known_devices"]),
        txns_last_hour=rng.randint(1, 3),
        new_payee=rng.random() < 0.1,
        minutes_since_last_txn=rng.randint(30, 720),
        last_txn_country=c["home_country"],
        scenario="clean",
        is_fraud=False,
    )


def fraud_txn(rng, cid, c) -> dict:
    start, end = _hours(c["usual_hours"])
    night = [h for h in range(24) if not start <= h < end]
    return dict(
        customer_id=cid,
        amount_gbp=round(rng.uniform(2, 8) * c["max_normal_amount_gbp"]
                         + rng.choice([0, 0, 5000]), 2),
        country=rng.choice(FOREIGN_COUNTRIES),
        category=rng.choice(RISKY_CATEGORIES),
        hour=rng.choice(night),
        device_id=rng.choice(BLOCKLISTED + ["device_new_" + str(rng.randint(100, 999))]),
        txns_last_hour=rng.randint(4, 12),
        new_payee=True,
        minutes_since_last_txn=rng.randint(3, 50),
        last_txn_country=c["home_country"],
        scenario="fraud",
        is_fraud=True,
    )


def borderline_txn(rng, cid, c) -> dict:
    """Clean transaction with one or two out-of-character twists."""
    txn = clean_txn(rng, cid, c)
    start, end = _hours(c["usual_hours"])
    twists = rng.sample(["big_amount", "off_hours", "new_category", "abroad"], rng.randint(1, 2))
    if "big_amount" in twists:
        txn["amount_gbp"] = round(min(rng.uniform(1.2, 2.5) * c["max_normal_amount_gbp"], 4900), 2)
        txn["new_payee"] = rng.random() < 0.5
    if "off_hours" in twists:
        txn["hour"] = rng.choice([h for h in range(24) if not start <= h < end])
    if "new_category" in twists:
        txn["category"] = rng.choice([x for x in CATEGORIES if x not in c["usual_categories"]])
    if "abroad" in twists:
        # Genuinely travelling: already abroad on the last transaction, so no
        # impossible-travel flag — just an unusual location.
        country = rng.choice(["US", "ES", "IT", "PT", "GR", "JP"])
        txn["country"] = txn["last_txn_country"] = country
    txn["scenario"] = "borderline"
    txn["is_fraud"] = rng.random() < BORDERLINE_FRAUD_RATE
    return txn


def main():
    rng = random.Random(SEED)
    customers = make_customers(rng)
    ids = list(customers)

    generated = (
        [clean_txn(rng, cid, customers[cid]) for cid in rng.choices(ids, k=N_CLEAN)]
        + [fraud_txn(rng, cid, customers[cid]) for cid in rng.choices(ids, k=N_FRAUD)]
        + [borderline_txn(rng, cid, customers[cid]) for cid in rng.choices(ids, k=N_BORDERLINE)]
    )
    rng.shuffle(generated)
    for n, txn in enumerate(generated, start=1004):
        txn["id"] = f"T{n}"
    transactions = DEMO_TRANSACTIONS + generated

    DATA_DIR.mkdir(exist_ok=True)

    with open(DATA_DIR / "customers.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["customer_id", "home_country", "typical_amount_gbp",
                         "max_normal_amount_gbp", "usual_categories", "usual_hours",
                         "known_devices"])
        for cid, c in customers.items():
            writer.writerow([cid, c["home_country"], c["typical_amount_gbp"],
                             c["max_normal_amount_gbp"], "|".join(c["usual_categories"]),
                             c["usual_hours"], "|".join(c["known_devices"])])

    fields = ["id", "customer_id", "amount_gbp", "country", "category", "hour",
              "device_id", "txns_last_hour", "new_payee", "minutes_since_last_txn",
              "last_txn_country", "scenario", "is_fraud"]
    with open(DATA_DIR / "transactions.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(transactions)

    print(f"Wrote {len(customers)} customers and {len(transactions)} transactions to {DATA_DIR}")


if __name__ == "__main__":
    main()
