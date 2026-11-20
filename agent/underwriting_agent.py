"""Credit underwriting agent: Strands Agents + Bedrock AgentCore SDK.

The agent talks to the local MCP server (mcp_server/server.py) for all data.

Local CLI chat:   uv run python agent/underwriting_agent.py "Underwrite APP0003"
AgentCore app:    uv run python agent/underwriting_agent.py --serve   (POST :8080/invocations)
Test the app:     curl -X POST localhost:8080/invocations -H 'Content-Type: application/json' \
                    -d '{"prompt": "Underwrite APP0003"}'

Env:
  MCP_URL      use a running HTTP MCP server (e.g. http://127.0.0.1:8000/mcp) instead of
               spawning the stdio server as a subprocess.
  BEDROCK_MODEL_ID  override the Bedrock model id (default: Strands' default model).
"""
import os
import sys
from pathlib import Path

from bedrock_agentcore.runtime import BedrockAgentCoreApp
from mcp import StdioServerParameters, stdio_client
from mcp.client.streamable_http import streamablehttp_client
from strands import Agent
from strands.models import BedrockModel
from strands.tools.mcp import MCPClient

ROOT = Path(__file__).resolve().parent.parent

SYSTEM_PROMPT = """You are a senior consumer credit underwriter.

For each application, gather evidence with the tools before deciding:
1. list_applicants / applicant profile (income, requested amount and term)
2. get_location -> then get_macro_economic_factors for that location
3. get_prev_credit_history
4. get_historic_bank_balance

Then estimate affordability (assume ~12% APR to approximate the monthly payment; compare
existing debt service + new payment against income) and weigh: credit score and delinquencies,
utilization, cash-flow stability and overdrafts, and local macro risk (unemployment trend,
regional delinquency rate).

Respond in this format:
**Decision:** APPROVE | APPROVE WITH CONDITIONS | REFER TO MANUAL REVIEW | DECLINE
**Risk tier:** Low / Medium / High
**Suggested limit / terms:** (amount, term, indicative rate)
**Key factors:** bullets, citing concrete numbers from the tools
**Conditions / next steps:** bullets
Never invent data; if a tool returns an error, say so and refer to manual review."""


def build_mcp_client() -> MCPClient:
    url = os.environ.get("MCP_URL")
    if url:
        return MCPClient(lambda: streamablehttp_client(url))
    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "mcp_server" / "server.py")],
    )
    return MCPClient(lambda: stdio_client(params))


def build_model():
    model_id = os.environ.get("BEDROCK_MODEL_ID")
    return BedrockModel(model_id=model_id) if model_id else None


mcp_client = build_mcp_client()
app = BedrockAgentCoreApp()


@app.entrypoint
def invoke(payload: dict) -> dict:
    """AgentCore entrypoint. payload: {"prompt": "..."}"""
    prompt = payload.get("prompt", "")
    with mcp_client:
        kwargs = {"model": m} if (m := build_model()) else {}
        agent = Agent(system_prompt=SYSTEM_PROMPT, tools=mcp_client.list_tools_sync(), **kwargs)
        result = agent(prompt)
    return {"result": str(result)}


if __name__ == "__main__":
    if "--serve" in sys.argv:
        app.run()
    else:
        question = " ".join(a for a in sys.argv[1:]) or "Underwrite applicant APP0001."
        print(invoke({"prompt": question})["result"])
