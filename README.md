# Credit Underwriting Agent

Mock-data credit underwriting, exposed as an MCP server (for Claude Desktop) and as a
Strands agent wrapped in the Bedrock AgentCore SDK.

```
data/*.csv  ──►  mcp_server/server.py (MCP tools)  ◄──  Claude Desktop (stdio)
                         ▲
                         └──────────  agent/underwriting_agent.py (Strands + AgentCore app)
```

## Data (CSV, regenerate with `uv run python scripts/generate_data.py`)
| File | Content |
|---|---|
| applicants.csv | 30 applicants, income, requested loan |
| locations.csv | address, `region_id`, housing status |
| macro_economic.csv | 10 regions x 8 quarters: unemployment, income, HPI, CPI, GDP, delinquency, fed rate |
| credit_history.csv | score, utilization, delinquencies, bankruptcies, inquiries, debt |
| bank_balances.csv | 12 months per applicant: balances, inflow/outflow, overdrafts, NSF |

Risk profiles (prime → deep subprime) are consistent across all four tables.

## MCP tools
`list_applicants`, `get_location`, `get_macro_economic_factors`, `get_prev_credit_history`, `get_historic_bank_balance`

## Claude Desktop (Windows, server runs in WSL)
1. Open Settings → Developer → Edit Config (`%APPDATA%\Claude\claude_desktop_config.json`).
2. Merge in `claude_desktop_config.snippet.json`.
3. Fully quit and restart Claude Desktop, then ask: *"Underwrite applicant APP0003 using the credit-underwriting tools."*

## Strands agent + AgentCore SDK
Needs AWS credentials with Bedrock model access (`aws configure` / env vars; set `BEDROCK_MODEL_ID` to override model).

```bash
uv run python agent/underwriting_agent.py "Underwrite APP0003"     # one-shot CLI
uv run python agent/underwriting_agent.py --serve                  # AgentCore app on :8080
curl -X POST localhost:8080/invocations -H 'Content-Type: application/json' \
     -d '{"prompt": "Underwrite APP0003"}'
```
By default the agent spawns the MCP server over stdio. To use a long-running HTTP server instead:
```bash
uv run python mcp_server/server.py --http      # http://127.0.0.1:8000/mcp
MCP_URL=http://127.0.0.1:8000/mcp uv run python agent/underwriting_agent.py "Underwrite APP0003"
```
Note: `mcp` is pinned `<2` (FastMCP API).
