"""The graph — this IS the orchestration.

    START -> orchestrator -+-> rules -------+-> adjudicator -+
                           +-> behavioural -+                |
                 +-------------------------------------------+
                 +-> review ------------> human_review --+-> audit -> END
                 +-> approve / decline -> finalise_auto -+

Rules and Behavioural are independent, so they run in parallel; the
Adjudicator waits for both. Every run ends at `audit`, which writes the
decision to the audit log whichever path it took.

The checkpointer is what lets the graph pause at human_review and resume later
with the human's verdict. MemorySaver keeps that in memory (fine for the CLI);
the dashboard passes a SQLite checkpointer so paused cases survive a restart.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from . import audit
from .agents.adjudicator import adjudicator_node
from .agents.behavioural import behavioural_node
from .agents.orchestrator import orchestrator_node
from .agents.rules import rules_node
from .observability import traced
from .state import FraudState

VERDICTS = ("approve", "decline")


def human_review_node(state: FraudState) -> dict:
    """Pause the run and hand the case to a human.

    The caller resumes with Command(resume=...) carrying either a plain
    "approve"/"decline" or {"decision": ..., "reviewer": ..., "note": ...}.
    Anything else is rejected — a human decision is the one input that moves
    money, so it is validated as strictly as a transaction.
    """
    answer = interrupt({
        "reason": "Borderline transaction — human decision required",
        "transaction": state["transaction"],
        "risk_score": state["risk_score"],
        "rule_flags": state.get("rule_flags", []),
        "behavioural_flags": state.get("behavioural_flags", []),
        "behavioural_reasoning": state.get("behavioural_reasoning", ""),
        "rationale": state["rationale"],
    })
    if isinstance(answer, str):
        answer = {"decision": answer}
    decision = str(answer.get("decision", "")).strip().lower()
    if decision not in VERDICTS:
        raise ValueError(f"Human verdict must be one of {VERDICTS}, got {decision!r}")
    return {
        "final_action": decision,
        "human_reviewed": True,
        "reviewer": str(answer.get("reviewer") or "unknown")[:100],
        "review_note": str(answer.get("note") or "")[:1000],
    }


def finalise_auto_node(state: FraudState) -> dict:
    """Auto cases: the final action is simply the recommended action."""
    return {"final_action": state["recommended_action"], "human_reviewed": False}


def audit_node(state: FraudState) -> dict:
    audit.record(state)
    return {}


def route_after_adjudication(state: FraudState) -> str:
    return "human_review" if state["recommended_action"] == "review" else "finalise_auto"


def build_graph(checkpointer=None):
    builder = StateGraph(FraudState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("rules", rules_node)
    builder.add_node("behavioural", behavioural_node)
    builder.add_node("adjudicator", adjudicator_node)
    builder.add_node("human_review", traced("human_review")(human_review_node))
    builder.add_node("finalise_auto", finalise_auto_node)
    builder.add_node("audit", audit_node)

    builder.add_edge(START, "orchestrator")
    builder.add_edge("orchestrator", "rules")
    builder.add_edge("orchestrator", "behavioural")
    builder.add_edge(["rules", "behavioural"], "adjudicator")
    builder.add_conditional_edges(
        "adjudicator",
        route_after_adjudication,
        {"human_review": "human_review", "finalise_auto": "finalise_auto"},
    )
    builder.add_edge("human_review", "audit")
    builder.add_edge("finalise_auto", "audit")
    builder.add_edge("audit", END)

    # The checkpointer is required for interrupt()/resume to work.
    return builder.compile(checkpointer=checkpointer or MemorySaver())
