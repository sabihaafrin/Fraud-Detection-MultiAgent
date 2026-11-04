"""Single place that builds the LLM.

Every agent calls get_llm() (via explain()), so switching provider
(Ollama -> Gemini -> OpenAI) is a one-file change. The provider package is
imported lazily inside the function so nothing is loaded until an agent
actually needs the model.
"""

import logging
import os
from functools import lru_cache

log = logging.getLogger(__name__)


def model_name() -> str:
    return os.getenv("LLM_MODEL", "llama3.2:3b")


@lru_cache(maxsize=1)
def get_llm():
    """Return a chat model, configured from environment variables.

    Runs locally through Ollama (no API key needed). LLM_MODEL overrides the
    model name; the model must already be pulled (`ollama pull llama3.2:3b`).
    OLLAMA_BASE_URL points at a non-default Ollama (e.g. in Docker).
    temperature=0 keeps the demo's judgements stable run-to-run; num_predict
    bounds the length (and so the time) of each explanation.
    """
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model_name(),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        num_predict=200,
        client_kwargs={"timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))},
    )


def explain(prompt: str, fallback: str) -> tuple[str, bool]:
    """Ask the LLM for an explanation; fall back to `fallback` if it fails.

    Explanations never affect a decision, so an LLM outage (Ollama not running,
    timeout, model not pulled) must not stop the pipeline. Returns the text and
    whether the fallback was used, so the audit log can record it.
    """
    try:
        llm = get_llm().with_retry(stop_after_attempt=2)
        text = llm.invoke(prompt).content.strip()
        if text:
            return text, False
        log.warning("LLM returned an empty explanation; using fallback")
    except Exception as e:  # noqa: BLE001 — any provider failure degrades the same way
        log.warning("LLM unavailable (%s: %s); using fallback explanation",
                    type(e).__name__, e)
    return fallback, True
