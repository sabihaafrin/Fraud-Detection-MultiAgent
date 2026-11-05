# Risk score is 0-100: below APPROVE_BELOW approves, at or above
# DECLINE_AT_OR_ABOVE declines, anything in between goes to a human.
APPROVE_BELOW = 35
DECLINE_AT_OR_ABOVE = 75

# Rules agent
HIGH_AMOUNT_GBP = 5000
MAX_TXNS_PER_HOUR = 5
IMPOSSIBLE_TRAVEL_MINUTES = 60
NEW_PAYEE_AMOUNT_GBP = 500
BLOCKLISTED_DEVICES = {"device_unknown_x", "device_bad_99"}

# Behavioural agent: risk added per signal
BEHAVIOURAL_WEIGHTS = {
    "above_normal_maximum": 30,
    "outside_usual_hours": 20,
    "unusual_category": 15,
    "away_from_home": 20,
}
