"""MCP server — exposes the fraud checks to other AI agents.

Any MCP client (Claude Desktop, Claude Code, an IDE assistant, another agent)
can score a transaction or look up a customer profile. The tools are
read-only by design: an external agent can ask "how risky is this?", but it
cannot approve or decline a payment — that authority stays with the graph's
thresholds and the human reviewer.

Run (stdio transport):   python -m src.mcp_server

Example client config (e.g. Claude Desktop's claude_desktop_config.json):
    {"mcpServers": {"fraud-detection-system": {
        "command": "<project>/.venv/Scripts/python.exe",
        "args": ["-m", "src.mcp_server"],
        "cwd": "<project>"}}}
"""

from mcp.server.mcpserver import MCPServer

from .evaluate import metrics, run_evaluation
from .models import InvalidTransaction
from .tools import get_customer_profile as profile_tool
from .tools import score_transaction as score_tool

server = MCPServer(
    name="fraud-detection-system",
    instructions="Read-only fraud checks: score a transaction, look up a customer's "
                 "normal behaviour, or get the system's evaluation metrics.",
)


@server.tool()
def score_transaction(transaction: dict) -> dict:
    """Score a payment for fraud risk with the deterministic Rules and
    Behavioural checks. `transaction` needs: id (T + digits), customer_id
    (C + digits), amount_gbp, country (2-letter), category, hour (0-23),
    device_id, txns_last_hour, new_payee, minutes_since_last_txn,
    last_txn_country. Returns flags, per-agent risk, the 0-100 risk score and
    the recommended action (approve | review | decline)."""
    try:
        return score_tool.invoke({"transaction": transaction})
    except InvalidTransaction as e:
        return {"error": str(e)}


@server.tool()
def get_customer_profile(customer_id: str) -> dict:
    """Return a customer's normal behaviour (home country, typical and maximum
    amounts, usual categories, hours and devices). Empty if unknown."""
    return profile_tool.invoke({"customer_id": customer_id})


@server.tool()
def evaluation_summary() -> dict:
    """Return the system's accuracy on the labelled synthetic dataset:
    detection rate, false-decline rate, missed-fraud rate and review rate."""
    return metrics(run_evaluation())


if __name__ == "__main__":
    server.run("stdio")
