"""The shared state that flows through the graph.

Every agent reads from and writes to this single object. LangGraph merges each
node's returned dict into it, so the Adjudicator can see what the Rules and
Behavioural agents wrote earlier in the run.

total=False means nodes may fill keys in gradually — the input only needs to
provide `transaction`. Rules and Behavioural run in parallel, so the keys they
both write (`trace`, `llm_fallbacks`) use an add reducer: their updates are
concatenated instead of one overwriting the other.
"""

import operator
from typing import Annotated, Any, TypedDict


class FraudState(TypedDict, total=False):
    # Input
    transaction: dict[str, Any]          # the event being judged

    # Added by the Orchestrator
    customer_history: dict[str, Any]     # this customer's normal behaviour

    # Added by the Rules agent
    rule_flags: list[str]                # e.g. ["high_amount", "impossible_travel"]
    rule_risk: int                       # 0-100 contribution from hard rules

    # Added by the Behavioural agent
    behavioural_flags: list[str]         # e.g. ["above_normal_maximum", "outside_usual_hours"]
    behavioural_anomaly: bool            # is this out of character?
    behavioural_risk: int                # 0-100 contribution from behaviour
    behavioural_reasoning: str           # the agent's explanation

    # Added by the Adjudicator
    risk_score: int                      # 0-100 overall
    rationale: str                       # human-readable justification
    recommended_action: str              # approve | decline | review

    # Final outcome
    final_action: str                    # approve | decline (what actually happens)
    human_reviewed: bool                 # was a human involved?
    reviewer: str                        # who made the human decision
    review_note: str                     # why they decided that way

    # Observability (appended to by every node)
    trace: Annotated[list[dict], operator.add]          # [{"agent": ..., "ms": ...}]
    llm_fallbacks: Annotated[list[str], operator.add]   # agents whose LLM call failed
