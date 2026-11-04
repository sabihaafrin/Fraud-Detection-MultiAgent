# Governance and human oversight

How the Fraud Detection System keeps a human in charge of the decisions that matter, and how
every decision can be explained after the fact.

## Who decides what

| Decision | Made by | Basis |
|---|---|---|
| Risk score (0–100) | Python code | Rules risk + Behavioural risk (`src/agents/adjudicator.py`), with fixed weights in `src/config.py` and `src/agents/rules.py` |
| Approve automatically | Thresholds | Score below `APPROVE_BELOW` (35) |
| Decline automatically | Thresholds | Score at or above `DECLINE_AT_OR_ABOVE` (75) |
| Everything in between | **A human reviewer** | The graph pauses (`interrupt()`) until a person approves or declines |
| Explanations | LLM (local `llama3.2:3b`) | Advisory text only, which cannot change any of the above |

The LLM never decides. That was a deliberate choice after testing: the
small local model misjudged simple comparisons (it called £1,400 "within" a
£900 limit), so letting it score made outcomes unreliable. See
[CODE_WALKTHROUGH.md](CODE_WALKTHROUGH.md).

## The human checkpoint

- **Trigger:** any case scoring 35–74 (9% of traffic on the evaluation set).
- **What the reviewer sees:** the transaction, the customer's normal behaviour,
  every rule flag and behavioural signal, each agent's risk, and both written
  explanations. That's available on the dashboard's **Review queue** tab or in
  the CLI.
- **What they must give:** approve or decline, with an optional reason. Nothing
  else is accepted (`src/graph.py`).
- **Durability:** paused cases are checkpointed to SQLite, so a restart doesn't
  lose a case waiting for review.

## Accountability: the audit log

Every decision, automatic or human, is appended to `results/audit_log.jsonl`
by the graph's final `audit` node, whichever path the case took. Each entry
records:

- the transaction ID, customer and amount
- all flags and per-agent risks, the score, and the recommended and final action
- whether a human decided, **who**, and **why**
- the LLM model and the thresholds in force at the time
- per-agent timings, and whether any LLM explanation fell back to a template

An example from a real dashboard run is in `results/sample_audit_log.jsonl`.

## Changing the policy

All decision boundaries live in `src/config.py`. To change one:

1. Edit the value.
2. Run `python -m src.evaluate` and compare the report.
3. Run `pytest`. `tests/test_evaluation.py` fails if detection drops below
   85%, any genuine customer is auto-declined, or more than 15% of traffic goes
   to review.
4. Commit the change together with the regenerated
   `results/evaluation_report.md`, so the policy and its measured effect are
   reviewed together.

## Known limits of this oversight

- The reviewer identity is self-declared (there's no login), so it's not fit
  for production as-is. See [SECURITY.md](../SECURITY.md).
- Thresholds were tuned on synthetic data and would need recalibrating on real
  traffic.
- Low-value fraud that looks normal apart from one signal is approved without a
  human ever seeing it (3 of 23 frauds). See [EVALUATION.md](EVALUATION.md).
