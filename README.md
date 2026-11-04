# SentinelAI

A multi-agent fraud detection system built with **LangGraph**. A transaction
flows through specialist agents that each judge it, an adjudicator combines
their findings into one risk score, and borderline cases **pause and escalate
to a human** before a final decision is made.

*Agentic AI Bootcamp — DAIM Lab, University of Hull — 4 November 2026*

---

## The flow

```
START → orchestrator → rules → behavioural → adjudicator ─┬─ approve/decline → finalise_auto → END
                                                          └─ review → human_review (⏸ pause) → END
```

| Agent | What it does | LLM? |
|---|---|---|
| **Orchestrator** | Attaches the customer's history to the case | No |
| **Rules** | Hard, deterministic checks (amount, velocity, impossible travel, blocklist) | No |
| **Behavioural** | Checks whether the transaction is out of character for *this* customer (amount, hour, category, country) | Explains |
| **Adjudicator** | Combines both into one 0–100 risk score + rationale | Explains |
| **Human review** | Receives borderline cases, returns an approve/decline verdict | Human |

The **graph itself is the orchestration** — the edges decide which agent runs
when. Every score, and the score → action mapping (`config.py`), is computed in
Python, so decisions are reproducible and auditable. The LLM turns the findings
into explanations a human reviewer can read — it never moves a score. (Small
local models like `llama3.2:3b` get numeric comparisons wrong, so letting them
score made the demo unreliable.)

---

## Project structure

```
Fraud-Detection-MultiAgent/
├── README.md
├── requirements.txt
├── .env.example           # copy to .env (git-ignored)
├── test.py                # quick check that the LLM responds
├── data/                  # datasets go here (git-ignored)
├── docs/
│   ├── setup-guide.md     # machine setup, step by step
│   ├── fraud-agents-proposal.md
│   └── CODE_WALKTHROUGH.md
└── src/
    ├── config.py          # all thresholds & rule parameters — tune here
    ├── state.py           # the shared state passed between agents
    ├── llm.py             # LLM factory (swap provider in one place)
    ├── sample_data.py     # synthetic transactions + customer history
    ├── graph.py           # nodes, edges, routing, HITL interrupt
    ├── main.py            # entry point
    └── agents/
        ├── orchestrator.py
        ├── rules.py
        ├── behavioural.py
        └── adjudicator.py
```

---

## Run it

First set up your machine with [docs/setup-guide.md](docs/setup-guide.md)
(Python, virtual environment, Ollama + `ollama pull llama3.2:3b`). Then, from
the project root with `(.venv)` active:

```bash
pip install -r requirements.txt
cp .env.example .env          # optional: change LLM_MODEL here
python test.py                # should print: setup works
python -m src.main
```

Run it as `python -m src.main`, not `python src/main.py` — the code uses
package imports.

You'll see each agent report in turn. The clean transaction auto-approves, the
obvious-fraud one auto-declines, and the borderline one stops and asks you to
decide on the console.

---

## How the human-in-the-loop works

The `human_review` node calls LangGraph's `interrupt()`, which suspends the
graph. `main.py` catches the interrupt, prints the case file, asks for a
verdict, then resumes the graph with `Command(resume=verdict)`. The
`MemorySaver` checkpointer is what makes pause-and-resume possible — without it,
`interrupt()` has nowhere to save the paused state.

---

## Extending it (stretch goals)

- **Real data** — replace `sample_data.py` with a loader for the PaySim or
  credit-card-fraud dataset. Nothing else changes as long as the transaction
  fields stay the same.
- **Network agent** — add a fourth specialist that checks whether the device /
  IP / email links to previously flagged accounts. One new node + one edge.
- **Case report** — have the adjudicator also draft a written case summary for
  the human reviewer.
- **Dashboard** — log every outcome and chart approve/decline/review rates.

---

## Switching LLM provider

Everything routes through `get_llm()` in `src/llm.py`, which currently uses a
local Ollama model (`llama3.2:3b`). To try a different Ollama model, pull it and
set `LLM_MODEL` in `.env`. To use a hosted provider instead (e.g. Gemini):
`pip install langchain-google-genai`, swap the import and class in that one
function, and set `GOOGLE_API_KEY` in `.env`. No agent code changes.
