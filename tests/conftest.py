"""Shared fixtures. No test needs Ollama: the LLM is replaced with a fake."""

import pytest
from langchain_core.language_models.fake_chat_models import FakeListChatModel

from src import llm
from src.sample_data import SAMPLE_TRANSACTIONS


@pytest.fixture(autouse=True)
def isolated_audit_log(tmp_path, monkeypatch):
    """Every test writes its audit log to a temp file, never results/."""
    path = tmp_path / "audit_log.jsonl"
    monkeypatch.setenv("AUDIT_LOG_PATH", str(path))
    return path


@pytest.fixture
def fake_llm(monkeypatch):
    """Replace the LLM with one that always answers the same explanation."""
    model = FakeListChatModel(responses=["Fake explanation for testing."])
    monkeypatch.setattr(llm, "get_llm", lambda: model)
    return model


@pytest.fixture
def broken_llm(monkeypatch):
    """Simulate Ollama being down: every LLM call raises."""
    def unavailable():
        raise ConnectionError("Ollama is not running")
    monkeypatch.setattr(llm, "get_llm", unavailable)


@pytest.fixture
def demo():
    """The three hand-picked demo transactions, keyed by id."""
    return {t["id"]: dict(t) for t in SAMPLE_TRANSACTIONS[:3]}
