"""Synthetic data for the demo.

Three transactions, deliberately chosen so one lands in each decision bucket:
T1001 clean -> approve, T1002 egregious -> decline, T1003 borderline -> review.

Swap this module for a real CSV loader (e.g. the PaySim or credit-card-fraud
dataset) when you want volume — nothing else in the system needs to change, as
long as the loader produces the same transaction fields.
"""

# One entry per customer: what "normal" looks like for them.
CUSTOMER_HISTORY = {
    "C001": {
        "home_country": "GB",
        "typical_amount_gbp": 60,
        "max_normal_amount_gbp": 400,
        "usual_categories": ["groceries", "transport", "dining"],
        "usual_hours": "07:00-22:00",
        "known_devices": ["device_a1"],
    },
    "C002": {
        "home_country": "FR",
        "typical_amount_gbp": 120,
        "max_normal_amount_gbp": 900,
        "usual_categories": ["electronics", "travel", "dining"],
        "usual_hours": "08:00-23:00",
        "known_devices": ["device_b2"],
    },
}

SAMPLE_TRANSACTIONS = [
    {
        # Clean: small, at home, usual category and device, normal hour.
        "id": "T1001",
        "customer_id": "C001",
        "amount_gbp": 42.50,
        "country": "GB",
        "category": "groceries",
        "hour": 18,
        "device_id": "device_a1",
        "txns_last_hour": 1,
        "new_payee": False,
        "minutes_since_last_txn": 240,
        "last_txn_country": "GB",
    },
    {
        # Egregious: huge amount, unknown + blocklisted device, impossible travel,
        # 3am, high velocity, new payee. Should trip multiple hard rules.
        "id": "T1002",
        "customer_id": "C001",
        "amount_gbp": 8800.00,
        "country": "NG",
        "category": "crypto",
        "hour": 3,
        "device_id": "device_unknown_x",
        "txns_last_hour": 9,
        "new_payee": True,
        "minutes_since_last_txn": 12,
        "last_txn_country": "GB",
    },
    {
        # Borderline: above the customer's normal maximum, late at night (outside
        # usual hours) and a new payee, but known device, home country, normal
        # velocity. Out of character, yet no single damning signal.
        "id": "T1003",
        "customer_id": "C002",
        "amount_gbp": 1400.00,
        "country": "FR",
        "category": "electronics",
        "hour": 2,
        "device_id": "device_b2",
        "txns_last_hour": 2,
        "new_payee": True,
        "minutes_since_last_txn": 180,
        "last_txn_country": "FR",
    },
]
