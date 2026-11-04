"""Tunable parameters, all in one place.

Every threshold the system uses lives here so a reviewer can see — and change —
the decision boundaries without reading any agent code.
"""

# --- Final decision thresholds (risk score is 0-100) ---
# score < APPROVE_BELOW            -> auto-approve
# score >= DECLINE_AT_OR_ABOVE     -> auto-decline
# everything in between            -> send to a human (review)
APPROVE_BELOW = 35
DECLINE_AT_OR_ABOVE = 75

# --- Rules-agent parameters ---
HIGH_AMOUNT_GBP = 5000          # single transaction above this is flagged
MAX_TXNS_PER_HOUR = 5           # more than this in an hour = velocity flag
IMPOSSIBLE_TRAVEL_MINUTES = 60  # country change faster than this = impossible travel
NEW_PAYEE_AMOUNT_GBP = 500      # new payee above this amount is flagged

# Devices/IPs known to be compromised.
BLOCKLISTED_DEVICES = {"device_unknown_x", "device_bad_99"}

# --- Behavioural-agent parameters ---
# Risk added for each way a transaction departs from the customer's own history.
BEHAVIOURAL_WEIGHTS = {
    "above_normal_maximum": 30,   # amount above their usual maximum
    "outside_usual_hours": 20,    # hour outside their usual window
    "unusual_category": 15,       # category they don't normally spend in
    "away_from_home": 20,         # country differs from their home country
}
