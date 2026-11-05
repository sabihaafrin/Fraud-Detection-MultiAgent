import operator
from typing import Annotated, Any, TypedDict


class FraudState(TypedDict, total=False):
    transaction: dict[str, Any]
    customer_history: dict[str, Any]

    rule_flags: list[str]
    rule_risk: int

    behavioural_flags: list[str]
    behavioural_anomaly: bool
    behavioural_risk: int
    behavioural_reasoning: str

    risk_score: int
    rationale: str
    recommended_action: str

    final_action: str
    human_reviewed: bool
    reviewer: str
    review_note: str

    # rules and behavioural run in parallel, so these lists are merged, not replaced
    trace: Annotated[list[dict], operator.add]
    llm_fallbacks: Annotated[list[str], operator.add]
