import logging
import os
from functools import lru_cache

log = logging.getLogger(__name__)


def model_name() -> str:
    return os.getenv("LLM_MODEL", "llama3.2:3b")


@lru_cache(maxsize=1)
def get_llm():
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=model_name(),
        base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
        num_predict=200,
        client_kwargs={"timeout": float(os.getenv("LLM_TIMEOUT_SECONDS", "60"))},
    )


def explain(prompt: str, fallback: str) -> tuple[str, bool]:
    # Explanations never change a decision, so if the LLM fails we use the fallback text.
    try:
        llm = get_llm().with_retry(stop_after_attempt=2)
        text = llm.invoke(prompt).content.strip()
        if text:
            return text, False
        log.warning("LLM returned an empty explanation; using fallback")
    except Exception as e:  # noqa: BLE001
        log.warning("LLM unavailable (%s: %s); using fallback explanation",
                    type(e).__name__, e)
    return fallback, True
