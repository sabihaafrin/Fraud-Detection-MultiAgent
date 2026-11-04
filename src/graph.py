"""The graph — this IS the orchestration.

Flow:
    START -> orchestrator -> rules -> behavioural -> adjudicator
                                                        |
                              (conditional on recommended_action)
                                   /                         \\
                          review  |                           | approve / decline
                                  v                           v
                           human_review                  finalise_auto
                                  \\                         /
                                   -----------> END <-------

The checkpointer (MemorySaver) is what lets the graph pause at the human_review
node and resume later with the human's verdict.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from .agents.adjudicator import adjudicator_node
from .agents.behavioural import behavioural_node
from .agents.orchestrator import orchestrator_node
from .agents.rules import rules_node
from .state import FraudState


def human_review_node(state: FraudState) -> dict:
    """Pause the run and hand the case to a human.

    interrupt() suspends the graph and surfaces this payload to the caller.
    Execution resumes here — returning the human's verdict — once the caller
    invokes the graph again with Command(resume=<verdict>).
    """
    verdict = interrupt({
        "reason": "Borderline transaction — human decision required",
        "transaction": state["transaction"],
        "risk_score": state["risk_score"],
        "rule_flags": state.get("rule_flags", []),
        "rationale": state["rationale"],
    })
    return {"final_action": verdict, "human_reviewed": True}


def finalise_auto_node(state: FraudState) -> dict:
    """Auto cases: the final action is simply the recommended action."""
    return {"final_action": state["recommended_action"], "human_reviewed": False}


def route_after_adjudication(state: FraudState) -> str:
    return "human_review" if state["recommended_action"] == "review" else "finalise_auto"


def build_graph():
    builder = StateGraph(FraudState)

    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("rules", rules_node)
    builder.add_node("behavioural", behavioural_node)
    builder.add_node("adjudicator", adjudicator_node)
    builder.add_node("human_review", human_review_node)
    builder.add_node("finalise_auto", finalise_auto_node)

    builder.add_edge(START, "orchestrator")
    builder.add_edge("orchestrator", "rules")
    builder.add_edge("rules", "behavioural")
    builder.add_edge("behavioural", "adjudicator")
    builder.add_conditional_edges(
        "adjudicator",
        route_after_adjudication,
        {"human_review": "human_review", "finalise_auto": "finalise_auto"},
    )
    builder.add_edge("human_review", END)
    builder.add_edge("finalise_auto", END)

    # The checkpointer is required for interrupt()/resume to work.
    return builder.compile(checkpointer=MemorySaver())
