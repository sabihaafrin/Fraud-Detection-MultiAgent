"""Adjudicator agent — combines the specialists into one decision.

The overall risk score is the Rules and Behavioural contributions added
together (capped at 100), and the score -> action mapping is a deterministic
threshold step (see config.py). Both are kept out of the LLM so routing is
defensible and reproducible — small local models are unreliable at arithmetic
and would over- or under-score. The LLM writes the rationale a human reviewer
reads.
"""

from .. import config
from ..llm import get_llm
from ..state import FraudState


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


def _action_from_score(score: int) -> str:
    if score < config.APPROVE_BELOW:
        return "approve"
    if score >= config.DECLINE_AT_OR_ABOVE:
        return "decline"
    return "review"


def adjudicator_node(state: FraudState) -> dict:
    score = min(state.get("rule_risk", 0) + state.get("behavioural_risk", 0), 100)
    action = _action_from_score(score)

    rationale = get_llm().invoke(PROMPT.format(
        rule_flags=state.get("rule_flags") or "none",
        rule_risk=state.get("rule_risk", 0),
        behavioural_flags=state.get("behavioural_flags") or "none",
        behavioural_risk=state.get("behavioural_risk", 0),
        behavioural_reasoning=state.get("behavioural_reasoning", ""),
        txn=state["transaction"],
        risk_score=score,
        action=action,
    )).content.strip()

    print(f"[Adjudicator]  score={score}  -> {action.upper()}")
    return {
        "risk_score": score,
        "rationale": rationale,
        "recommended_action": action,
    }
