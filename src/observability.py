"""Logging and per-agent tracing.

`traced` wraps a graph node: it times the node and appends an entry to the
state's `trace` list, so every run records which agents ran, in what order and
how long each took. The trace ends up in the audit log and on the dashboard.
"""

import functools
import logging
import time


def setup_logging(level: int = logging.INFO) -> None:
    """Console output in the same "[Agent]  details" style the demo prints."""
    logging.basicConfig(level=level, format="%(message)s")
    # Keep third-party chatter (HTTP calls to Ollama) out of the demo output.
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def traced(agent: str):
    def decorator(node):
        @functools.wraps(node)
        def wrapper(state):
            start = time.perf_counter()
            update = node(state)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 1)
            return {**update, "trace": [{"agent": agent, "ms": elapsed_ms}]}
        return wrapper
    return decorator
