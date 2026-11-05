import functools
import logging
import time


def setup_logging(level: int = logging.INFO) -> None:
    logging.basicConfig(level=level, format="%(message)s")
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


# Times a graph node and adds an entry to the state's trace list.
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
