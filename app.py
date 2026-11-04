"""Fraud Detection System dashboard — run the demo, review flagged cases, see the audit log.

    streamlit run app.py

Tabs:
  Run           push transactions (from the dataset, or one you enter) through
                the multi-agent graph and watch each agent's findings
  Review queue  cases the graph paused on; approve or decline as the human
                reviewer — the graph resumes with your verdict
  Audit log     every decision the system has made, and who made it

Paused cases are checkpointed to SQLite (results/checkpoints.sqlite), so the
review queue survives a dashboard restart.
"""

import json
import os
import sqlite3
import urllib.request
import uuid
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from src import audit, config
from src.graph import build_graph
from src.llm import model_name
from src.models import InvalidTransaction
from src.observability import setup_logging
from src.sample_data import CUSTOMER_HISTORY, LABELS, SAMPLE_TRANSACTIONS

CHECKPOINT_DB = Path(os.getenv("CHECKPOINT_DB",
                               Path(__file__).resolve().parent / "results" / "checkpoints.sqlite"))
ACTION_ICON = {"approve": "✅", "review": "⏸️", "decline": "⛔"}

load_dotenv()
setup_logging()
st.set_page_config(page_title="Fraud Detection System", page_icon="🛡️", layout="wide")


# --- Graph and checkpoints ------------------------------------------------------

@st.cache_resource
def get_graph():
    CHECKPOINT_DB.parent.mkdir(exist_ok=True)
    conn = sqlite3.connect(CHECKPOINT_DB, check_same_thread=False)
    saver = SqliteSaver(conn)
    return build_graph(saver), saver


def pending_reviews() -> list[dict]:
    """Every thread currently paused at human_review, oldest first."""
    graph, saver = get_graph()
    threads = dict.fromkeys(c.config["configurable"]["thread_id"] for c in saver.list(None))
    cases = []
    for thread_id in threads:
        cfg = {"configurable": {"thread_id": thread_id}}
        snapshot = graph.get_state(cfg)
        if snapshot.next == ("human_review",) and snapshot.tasks and snapshot.tasks[0].interrupts:
            cases.append({"thread_id": thread_id, "config": cfg,
                          "payload": snapshot.tasks[0].interrupts[0].value,
                          "state": snapshot.values})
    return list(reversed(cases))


def run_transaction(txn: dict) -> dict:
    graph, _ = get_graph()
    thread_id = f"{txn['id']}-{uuid.uuid4().hex[:8]}"
    return graph.invoke({"transaction": txn},
                        config={"configurable": {"thread_id": thread_id}})


def ollama_status() -> tuple[bool, str]:
    try:
        with urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2) as r:
            models = [m["name"] for m in json.load(r).get("models", [])]
        if model_name() in models:
            return True, f"Ollama running · `{model_name()}` ready"
        return False, f"Ollama running, but `{model_name()}` not pulled"
    except Exception:  # noqa: BLE001
        return False, "Ollama not reachable — explanations will use templates"


# --- Shared rendering ---------------------------------------------------------

def render_findings(state: dict) -> None:
    c1, c2, c3 = st.columns(3)
    c1.metric("Rules risk", f"{state.get('rule_risk', 0)}/100")
    c2.metric("Behavioural risk", f"{state.get('behavioural_risk', 0)}/100")
    c3.metric("Overall risk score", f"{state.get('risk_score', 0)}/100")
    st.markdown(f"**Rule flags:** {', '.join(state.get('rule_flags') or []) or 'none'}  \n"
                f"**Behavioural signals:** "
                f"{', '.join(state.get('behavioural_flags') or []) or 'none'}")
    st.markdown(f"**Behavioural agent:** {state.get('behavioural_reasoning', '')}")
    st.markdown(f"**Adjudicator rationale:** {state.get('rationale', '')}")
    if state.get("llm_fallbacks"):
        st.caption(f"LLM unavailable for {', '.join(state['llm_fallbacks'])} — "
                   "template explanation used; decision unaffected.")
    if state.get("trace"):
        st.caption("Agent timings: " + " → ".join(
            f"{s['agent']} {s['ms']:.0f} ms" for s in state["trace"]))


def render_transaction(txn: dict) -> None:
    st.dataframe(pd.DataFrame([txn]), hide_index=True, width="stretch")


# --- Sidebar ------------------------------------------------------------------

with st.sidebar:
    st.title("🛡️ Fraud Detection System")
    st.caption("Multi-agent fraud detection with a human-in-the-loop checkpoint")
    ok, msg = ollama_status()
    (st.success if ok else st.warning)(msg)
    st.text_input("Reviewer name", key="reviewer", value="analyst",
                  help="Recorded in the audit log with every human decision.")
    st.markdown("**Decision thresholds** (`src/config.py`)")
    st.markdown(f"- approve if score < **{config.APPROVE_BELOW}**\n"
                f"- decline if score ≥ **{config.DECLINE_AT_OR_ABOVE}**\n"
                f"- otherwise → human review")

pending = pending_reviews()
tab_run, tab_review, tab_audit = st.tabs(
    ["Run", f"Review queue ({len(pending)})", "Audit log"])


# --- Run ----------------------------------------------------------------------

with tab_run:
    st.subheader("Run transactions through the agents")
    st.caption("Orchestrator → Rules ∥ Behavioural → Adjudicator → approve / decline, "
               "or pause for a human. Each transaction takes a few seconds per LLM "
               "explanation.")

    ids = [t["id"] for t in SAMPLE_TRANSACTIONS]
    by_id = {t["id"]: t for t in SAMPLE_TRANSACTIONS}
    chosen = st.multiselect(
        "Transactions", ids, default=ids[:3],
        format_func=lambda i: f"{i} · £{by_id[i]['amount_gbp']:,.2f} · "
                              f"{by_id[i]['category']} · {LABELS[i]['scenario']}",
        help="T1001-T1003 are the demo: one clean, one fraud, one borderline.")

    with st.expander("…or enter a transaction"):
        with st.form("custom"):
            a, b, c = st.columns(3)
            custom = {
                "id": a.text_input("ID", "T9001"),
                "customer_id": b.selectbox("Customer", list(CUSTOMER_HISTORY)),
                "amount_gbp": c.number_input("Amount (£)", 0.01, 1_000_000.0, 250.0),
                "country": a.text_input("Country (2 letters)", "GB"),
                "category": b.text_input("Category", "electronics"),
                "hour": c.number_input("Hour (0-23)", 0, 23, 14),
                "device_id": a.text_input("Device", "device_a1"),
                "txns_last_hour": b.number_input("Transactions in last hour", 0, 10_000, 1),
                "new_payee": c.checkbox("New payee"),
                "minutes_since_last_txn": a.number_input("Minutes since last", 0, 10**6, 120),
                "last_txn_country": b.text_input("Last transaction country", "GB"),
            }
            run_custom = st.form_submit_button("Run this transaction")

    to_run = [custom] if run_custom else []
    if st.button("Run selected", type="primary", disabled=not chosen):
        to_run = [by_id[i] for i in chosen]

    for txn in to_run:
        with st.status(f"Running {txn['id']}…", expanded=True) as status:
            try:
                result = run_transaction(txn)
            except InvalidTransaction as e:
                status.update(label=f"{txn['id']} rejected", state="error")
                st.error(str(e))
                continue
            if "__interrupt__" in result:
                status.update(label=f"⏸️ {txn['id']} — paused for human review "
                                    f"(score {result['risk_score']})", state="running")
                st.info("Sent to the **Review queue** tab.")
            else:
                action = result["final_action"]
                status.update(label=f"{ACTION_ICON[action]} {txn['id']} — {action.upper()} "
                                    f"automatically (score {result['risk_score']})",
                              state="complete")
            render_transaction(result["transaction"])
            render_findings(result)
    if to_run:
        st.button("Refresh review queue")


# --- Review queue -------------------------------------------------------------

with tab_review:
    st.subheader("Cases waiting for a human decision")
    if not pending:
        st.info("No cases waiting. Run T1003 (or any borderline transaction) to create one.")
    for case in pending:
        p = case["payload"]
        txn = p["transaction"]
        with st.container(border=True):
            st.markdown(f"### {txn['id']} · £{txn['amount_gbp']:,.2f} · "
                        f"customer {txn['customer_id']} · score {p['risk_score']}/100")
            st.warning(f"**Why this needs you:** the score of {p['risk_score']} is above the "
                       f"auto-approve limit (< {config.APPROVE_BELOW}) but below the "
                       f"auto-decline limit (≥ {config.DECLINE_AT_OR_ABOVE}), so the "
                       f"system won't decide on its own.")
            render_transaction(txn)
            render_findings(case["state"])
            with st.expander(f"Customer {txn['customer_id']}'s normal behaviour"):
                st.json(CUSTOMER_HISTORY.get(txn["customer_id"], {}))
            note = st.text_input("Reason for your decision", key=f"note-{case['thread_id']}")
            approve, decline, _ = st.columns([1, 1, 4])
            verdict = None
            if approve.button("✅ Approve", key=f"a-{case['thread_id']}"):
                verdict = "approve"
            if decline.button("⛔ Decline", key=f"d-{case['thread_id']}"):
                verdict = "decline"
            if verdict:
                graph, _ = get_graph()
                graph.invoke(Command(resume={"decision": verdict,
                                             "reviewer": st.session_state.reviewer,
                                             "note": note}), config=case["config"])
                st.toast(f"{txn['id']} {verdict}d by {st.session_state.reviewer}")
                st.rerun()


# --- Audit log ----------------------------------------------------------------

with tab_audit:
    st.subheader("Audit log")
    st.caption(f"Every decision, appended to `{audit.audit_path().name}` — "
               "including who made each human decision and why.")
    entries = audit.read_all()
    if not entries:
        st.info("No decisions yet. Run a transaction first.")
    else:
        df = pd.DataFrame(entries[::-1])
        cols = ["timestamp", "transaction_id", "amount_gbp", "risk_score",
                "recommended_action", "final_action", "human_reviewed", "reviewer",
                "review_note", "llm_fallbacks"]
        st.dataframe(df[cols], hide_index=True, width="stretch")
        st.download_button("Download audit log (JSONL)",
                           "\n".join(json.dumps(e) for e in entries),
                           file_name="audit_log.jsonl")
