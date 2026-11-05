# Security

This is a bootcamp prototype that only uses synthetic data.

## What we handle

- **Prompt injection**: transaction fields are validated in `src/models.py`
  before any agent or prompt sees them. Text fields only allow short values
  from a fixed set of characters, and unknown fields are rejected.
- **The LLM can't change a decision**: scores and actions are calculated in
  Python. The model only writes explanations.
- **Human verdicts**: only `approve` or `decline` is accepted when a paused
  case is resumed.
- **info**: no API keys are needed because the model runs locally. `.env`
  is in `.gitignore`.
- **Dependencies**: versions are pinned in `requirements.txt`, and `pip-audit`
  runs in CI.

These are tested in `tests/test_security.py`.

## Limitations

- The dashboard has no login, so the reviewer name is typed in by hand.
- The LLM explanations can get numbers wrong. Reviewers should go by the flags
  and scores shown next to them.
