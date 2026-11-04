"""Single place that builds the LLM.

Every agent calls get_llm(), so switching provider (Ollama -> Gemini -> OpenAI)
is a one-file change. The provider package is imported lazily inside the
function so nothing is loaded until an agent actually needs the model.
"""

import os
from functools import lru_cache


@lru_cache(maxsize=1)
def get_llm():
    """Return a chat model, configured from environment variables.

    Runs locally through Ollama (no API key needed). LLM_MODEL overrides the
    model name; the model must already be pulled (`ollama pull llama3.2:3b`).
    temperature=0 keeps the demo's judgements stable run-to-run.
    """
    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=os.getenv("LLM_MODEL", "llama3.2:3b"),
        temperature=0,
    )
