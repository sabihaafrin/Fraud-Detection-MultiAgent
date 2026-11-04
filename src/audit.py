"""Append-only audit log of every decision.

One JSON line per transaction: what each agent found, the score, the
recommended and final action, whether a human decided (and who, and why), the
model and thresholds in force, and per-agent timings. This is the record a
fraud team or regulator would ask for — and it lets any decision be replayed.

AUDIT_LOG_PATH overrides the location (the tests point it at a temp file).
"""

import json
import os
from datetime import UTC, datetime
from pathlib import Path

from . import config
from .llm import model_name

DEFAULT_PATH = Path(__file__).resolve().parent.parent / "results" / "audit_log.jsonl"


def audit_path() -> Path:
    return Path(os.getenv("AUDIT_LOG_PATH", DEFAULT_PATH))


def record(state: dict) -> dict:
    entry = {
        "timestamp": datetime.now(UTC).isoformat(timespec="seconds"),
        "transaction_id": state["transaction"]["id"],
        "customer_id": state["transaction"]["customer_id"],
        "amount_gbp": state["transaction"]["amount_gbp"],
        "rule_flags": state.get("rule_flags", []),
        "rule_risk": state.get("rule_risk"),
        "behavioural_flags": state.get("behavioural_flags", []),
        "behavioural_risk": state.get("behavioural_risk"),
        "risk_score": state.get("risk_score"),
        "recommended_action": state.get("recommended_action"),
        "final_action": state.get("final_action"),
        "human_reviewed": state.get("human_reviewed", False),
        "reviewer": state.get("reviewer"),
        "review_note": state.get("review_note"),
        "rationale": state.get("rationale"),
        "llm_model": model_name(),
        "llm_fallbacks": state.get("llm_fallbacks", []),
        "thresholds": {"approve_below": config.APPROVE_BELOW,
                       "decline_at_or_above": config.DECLINE_AT_OR_ABOVE},
        "trace": state.get("trace", []),
    }
    path = audit_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return entry


def read_all() -> list[dict]:
    path = audit_path()
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
