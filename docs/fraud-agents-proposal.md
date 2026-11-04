# Fraud Detection System — Project Proposal

*Agentic AI Bootcamp — DAIM Lab, University of Hull — 4 November 2026*

**Team name:** Fraud Detection System
**Project title:** Fraud Detection System — a multi-agent fraud detection system
**Agent type:** Fraud Detection Agent (multi-agent)
**Framework:** LangGraph (ReAct loop + human-in-the-loop checkpoint)

---

## 1. What problem are we solving?

Fraud detection has to decide, for every incoming transaction, whether it is legitimate or fraudulent — fast enough to act before the money moves. The whole challenge is a trade-off: block too aggressively and you decline genuine customers; block too loosely and fraud gets through. A single model struggles to balance this, and the hardest cases always need a human to make the final call.

## 2. Who will benefit?

- **Banks, payment providers and fintechs** that need to screen transactions in real time.
- **Fraud analysts**, who get the borderline cases pre-investigated with the reasoning already laid out, instead of raw alerts.
- **Customers**, who face fewer wrongly declined payments.

## 3. What is the proposed solution?

A team of specialist agents coordinated by a supervisor, rather than one agent doing everything. For our MVP:

- **Orchestrator** — receives the transaction, dispatches it to the specialists, gathers their findings, and decides or escalates.
- **Rules agent** — deterministic checks: amount thresholds, transaction velocity, impossible-travel, blocklisted devices/IPs. Fast and fully explainable.
- **Behavioural agent** — compares the transaction against the customer's own history. "Is this out of character for this account?"
- **Adjudicator agent** — combines the specialist outputs into one risk score and a recommended action (approve / decline / review), with a written rationale.
- **Human-in-the-loop checkpoint** — anything landing in "review" pauses and escalates to a human, who approves or rejects; that decision is logged.

Built on LangGraph so the agents run as explicit graph nodes, and the human checkpoint is a real pause in the flow — not an afterthought. Demonstrated over a small synthetic transaction set with cases that clearly fall into each decision bucket.

## 4. What would success look like?

A working end-to-end prototype by the showcase where:

- a clearly fraudulent transaction is **auto-declined**,
- a clearly clean one is **auto-approved**, and
- a borderline one **pauses and escalates to a human**, whose verdict is recorded.

The headline we're demonstrating is clean multi-agent coordination and a genuine human-in-the-loop safeguard — not state-of-the-art detection accuracy.

## 5. Skills we are looking for

- **Python** — comfortable building and wiring up the agents (essential).
- **LangGraph / LangChain** (or willingness to learn on the day) — framework for the agent graph.
- **Data wrangling** — preparing the sample transaction data and the behavioural history lookup.
- **Fraud / risk domain interest** — useful for shaping sensible rules and thresholds.
- **Front-end / dashboard** — nice-to-have, for presenting the outcomes in the showcase.
