import logging

from .. import config
from ..llm import explain
from ..observability import traced
from ..state import FraudState

log = logging.getLogger(__name__)


PROMPT = """You are the Behavioural Analysis agent in a fraud detection system.
In one or two sentences, explain to a fraud analyst how this transaction
compares with the customer's normal behaviour.

Customer's normal behaviour:
{history}

Current transaction:
{txn}

These checks have already been computed and are correct. Base your
explanation on them and do not contradict them:
- Out-of-character signals: {signals}
- Behavioural risk: {risk}/100

Write only the explanation, no preamble."""


def _within_hours(hour: int, usual_hours: str) -> bool:
    start, end = (int(part.split(":")[0]) for part in usual_hours.split("-"))
    if start <= end:
        return start <= hour < end
    return hour >= start or hour < end


def _signals(txn: dict, history: dict) -> list[str]:
    if not history:
        return []
    signals = []
    if txn["amount_gbp"] > history["max_normal_amount_gbp"]:
        signals.append("above_normal_maximum")
    if not _within_hours(txn["hour"], history["usual_hours"]):
        signals.append("outside_usual_hours")
    if txn["category"] not in history["usual_categories"]:
        signals.append("unusual_category")
    if txn["country"] != history["home_country"]:
        signals.append("away_from_home")
    return signals


def evaluate_behaviour(txn: dict, history: dict) -> tuple[list[str], int]:
    signals = _signals(txn, history)
    return signals, min(sum(config.BEHAVIOURAL_WEIGHTS[s] for s in signals), 100)


@traced("behavioural")
def behavioural_node(state: FraudState) -> dict:
    txn = state["transaction"]
    history = state.get("customer_history", {})

    signals, risk = evaluate_behaviour(txn, history)

    fallback = (f"Out-of-character signals: {', '.join(signals)} (behavioural risk {risk}/100)."
                if signals else "Fits the customer's normal behaviour (behavioural risk 0/100).")
    reasoning, used_fallback = explain(PROMPT.format(
        history=history,
        txn=txn,
        signals=signals or "none",
        risk=risk,
    ), fallback)

    log.info(f"[Behavioural]  signals={signals or 'none'}  risk={risk}")
    return {
        "behavioural_flags": signals,
        "behavioural_anomaly": bool(signals),
        "behavioural_risk": risk,
        "behavioural_reasoning": reasoning,
        "llm_fallbacks": ["behavioural"] if used_fallback else [],
    }
