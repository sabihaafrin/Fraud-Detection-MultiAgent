import pytest
from langgraph.types import Command

from src import audit
from src.graph import build_graph


def run(graph, txn, thread="t"):
    return graph.invoke({"transaction": txn}, config={"configurable": {"thread_id": thread}})


def test_clean_transaction_is_auto_approved(fake_llm, demo):
    result = run(build_graph(), demo["T1001"])
    assert result["final_action"] == "approve"
    assert result["human_reviewed"] is False
    assert result["rationale"] == "Fake explanation for testing."


def test_obvious_fraud_is_auto_declined(fake_llm, demo):
    result = run(build_graph(), demo["T1002"])
    assert result["recommended_action"] == "decline"
    assert result["final_action"] == "decline"


def test_borderline_pauses_for_human_then_resumes(fake_llm, demo):
    graph = build_graph()
    cfg = {"configurable": {"thread_id": "hitl"}}

    paused = graph.invoke({"transaction": demo["T1003"]}, config=cfg)
    assert "__interrupt__" in paused
    payload = paused["__interrupt__"][0].value
    assert payload["risk_score"] == 60
    assert payload["behavioural_flags"] == ["above_normal_maximum", "outside_usual_hours"]
    assert graph.get_state(cfg).next == ("human_review",)

    result = graph.invoke(Command(resume={"decision": "decline", "reviewer": "analyst1",
                                          "note": "customer unreachable"}), config=cfg)
    assert result["final_action"] == "decline"
    assert result["human_reviewed"] is True
    assert result["reviewer"] == "analyst1"


def test_invalid_human_verdict_is_rejected(fake_llm, demo):
    graph = build_graph()
    cfg = {"configurable": {"thread_id": "bad-verdict"}}
    graph.invoke({"transaction": demo["T1003"]}, config=cfg)
    with pytest.raises(ValueError, match="Human verdict"):
        graph.invoke(Command(resume="maybe"), config=cfg)


def test_rules_and_behavioural_both_run_and_are_traced(fake_llm, demo):
    result = run(build_graph(), demo["T1001"])
    agents = [step["agent"] for step in result["trace"]]
    assert agents[0] == "orchestrator"
    assert set(agents[1:3]) == {"rules", "behavioural"}
    assert agents[3] == "adjudicator"
    assert all(step["ms"] >= 0 for step in result["trace"])


def test_every_decision_is_audited(fake_llm, demo, isolated_audit_log):
    graph = build_graph()
    run(graph, demo["T1001"], "a1")
    run(graph, demo["T1002"], "a2")
    entries = audit.read_all()
    assert [e["transaction_id"] for e in entries] == ["T1001", "T1002"]
    assert entries[1]["final_action"] == "decline"
    assert entries[1]["thresholds"] == {"approve_below": 35, "decline_at_or_above": 75}
    assert {s["agent"] for s in entries[1]["trace"]} >= {"rules", "behavioural", "adjudicator"}


def test_human_decision_is_audited_with_reviewer(fake_llm, demo):
    graph = build_graph()
    cfg = {"configurable": {"thread_id": "audit-hitl"}}
    graph.invoke({"transaction": demo["T1003"]}, config=cfg)
    graph.invoke(Command(resume={"decision": "approve", "reviewer": "analyst2",
                                 "note": "customer confirmed by phone"}), config=cfg)
    entry = audit.read_all()[-1]
    assert entry["human_reviewed"] is True
    assert entry["reviewer"] == "analyst2"
    assert entry["review_note"] == "customer confirmed by phone"
    assert entry["recommended_action"] == "review"
    assert entry["final_action"] == "approve"


def test_llm_outage_falls_back_without_changing_decision(broken_llm, demo):
    result = run(build_graph(), demo["T1002"])
    assert result["final_action"] == "decline"
    assert result["risk_score"] == 100
    assert sorted(result["llm_fallbacks"]) == ["adjudicator", "behavioural"]
    assert "blocklisted_device" in result["rationale"]
    assert audit.read_all()[-1]["llm_fallbacks"]


def test_paused_case_survives_restart_with_sqlite(fake_llm, demo, tmp_path):
    import sqlite3

    from langgraph.checkpoint.sqlite import SqliteSaver

    db = tmp_path / "checkpoints.sqlite"
    cfg = {"configurable": {"thread_id": "persist"}}

    with sqlite3.connect(db, check_same_thread=False) as conn:
        build_graph(SqliteSaver(conn)).invoke({"transaction": demo["T1003"]}, config=cfg)

    with sqlite3.connect(db, check_same_thread=False) as conn:
        graph = build_graph(SqliteSaver(conn))
        assert graph.get_state(cfg).next == ("human_review",)
        result = graph.invoke(Command(resume="approve"), config=cfg)
    assert result["final_action"] == "approve"
