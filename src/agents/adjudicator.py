"""Adjudicator agent — combines the specialists into one decision.

The overall risk score is the Rules and Behavioural contributions added
together (capped at 100), and the score -> action mapping is a deterministic
threshold step (see config.py). Both are kept out of the LLM so routing is
defensible and reproducible — small local models are unreliable at arithmetic
and would over- or under-score. The LLM writes the rationale a human reviewer
reads; if it is unavailable, a template rationale is used instead.
"""

import logging

from .. import config
from ..llm import explain
from ..observability import traced
from ..state import FraudState

log = logging.getLogger(__name__)


PROMPT = """You are the Adjudicator agent in a fraud detection system.
Write a short rationale (two or three sentences) for a human fraud reviewer,
explaining the decision below.

Rules agent (hard, deterministic checks):
- Triggered rules: {rule_flags}
- Rules risk contribution: {rule_risk}/100

Behavioural agent (fit to customer's history):
- Out-of-character signals: {behavioural_flags}
- Behavioural risk: {behavioural_risk}/100
- Reasoning: {behavioural_reasoning}

Transaction: {txn}

Decision (already made — explain it, do not change it):
- Overall risk score: {risk_score}/100
- Recommended action: {action}

Write only the rationale, no preamble."""


def _action_from_score(score: int, approve_below: int, decline_at_or_above: int) -> str:
    if score < approve_below:
        return "approve"
    if score >= decline_at_or_above:
        return "decline"
    return "review"


def adjudicate(rule_risk: int, behavioural_risk: int,
               approve_below: int | None = None,
               decline_at_or_above: int | None = None) -> tuple[int, str]:
    """Combine the specialists' risks into an overall score and an action.

    Thresholds default to config.py; pass others to test alternatives.
    """
    score = min(rule_risk + behavioural_risk, 100)
    action = _action_from_score(
        score,
        config.APPROVE_BELOW if approve_below is None else approve_below,
        config.DECLINE_AT_OR_ABOVE if decline_at_or_above is None else decline_at_or_above,
    )
    return score, action


@traced("adjudicator")
def adjudicator_node(state: FraudState) -> dict:
    rule_flags = state.get("rule_flags") or []
    behavioural_flags = state.get("behavioural_flags") or []
    score, action = adjudicate(state.get("rule_risk", 0), state.get("behavioural_risk", 0))

    fallback = (f"Risk score {score}/100 -> {action}. "
                f"Rules triggered: {', '.join(rule_flags) or 'none'} "
                f"(risk {state.get('rule_risk', 0)}). "
                f"Behavioural signals: {', '.join(behavioural_flags) or 'none'} "
                f"(risk {state.get('behavioural_risk', 0)}).")
    rationale, used_fallback = explain(PROMPT.format(
        rule_flags=rule_flags or "none",
        rule_risk=state.get("rule_risk", 0),
        behavioural_flags=behavioural_flags or "none",
        behavioural_risk=state.get("behavioural_risk", 0),
        behavioural_reasoning=state.get("behavioural_reasoning", ""),
        txn=state["transaction"],
        risk_score=score,
        action=action,
    ), fallback)

    log.info(f"[Adjudicator]  score={score}  -> {action.upper()}")
    return {
        "risk_score": score,
        "rationale": rationale,
        "recommended_action": action,
        "llm_fallbacks": ["adjudicator"] if used_fallback else [],
    }
