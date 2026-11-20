"""Credit underwriting MCP server (stdio by default, streamable-http optional).

Tools (all backed by CSV files in ./data):
  - list_applicants
  - get_location
  - get_macro_economic_factors
  - get_prev_credit_history
  - get_historic_bank_balance

Run:
  uv run python mcp_server/server.py                 # stdio  (Claude Desktop)
  uv run python mcp_server/server.py --http          # http://127.0.0.1:8000/mcp (Strands agent / AgentCore)
"""
import csv
import statistics
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

DATA = Path(__file__).resolve().parent.parent / "data"

mcp = FastMCP("credit-underwriting", host="127.0.0.1", port=8000)


def _read(name: str) -> list[dict]:
    with open(DATA / name, newline="") as f:
        return list(csv.DictReader(f))


def _num(v: str):
    try:
        f = float(v)
        return int(f) if f.is_integer() and "." not in v else f
    except (TypeError, ValueError):
        return v


def _typed(row: dict) -> dict:
    return {k: _num(v) for k, v in row.items()}


def _find(name: str, applicant_id: str) -> list[dict]:
    return [r for r in _read(name) if r["applicant_id"].upper() == applicant_id.strip().upper()]


@mcp.tool()
def list_applicants() -> list[dict]:
    """List all loan applicants with their basic profile and requested loan
    (id, name, age, employment type, annual income, requested amount/term)."""
    return [_typed(r) for r in _read("applicants.csv")]


@mcp.tool()
def get_location(applicant_id: str) -> dict:
    """Get the residential location of an applicant: street, city, state, zip,
    region_id (use this with get_macro_economic_factors), years at address and
    housing status (Rent / Own-Mortgage / Own-Outright)."""
    rows = _find("locations.csv", applicant_id)
    if not rows:
        return {"error": f"No location found for applicant '{applicant_id}'"}
    return _typed(rows[0])


@mcp.tool()
def get_macro_economic_factors(region_id: str = "", applicant_id: str = "", quarters: int = 4) -> dict:
    """Get macro-economic indicators for a location: unemployment, median household
    income, home price growth, CPI inflation, GDP growth, regional loan delinquency
    rate, cost of living and fed funds rate, plus the trend over recent quarters.

    Provide either region_id (e.g. 'TX-AUS') or applicant_id (region is looked up
    from the applicant's location). `quarters` = how many recent quarters (1-8)."""
    if not region_id:
        if not applicant_id:
            return {"error": "Provide region_id or applicant_id"}
        loc = _find("locations.csv", applicant_id)
        if not loc:
            return {"error": f"No location found for applicant '{applicant_id}'"}
        region_id = loc[0]["region_id"]

    rows = [r for r in _read("macro_economic.csv") if r["region_id"].upper() == region_id.upper()]
    if not rows:
        return {"error": f"Unknown region_id '{region_id}'"}
    rows.sort(key=lambda r: r["quarter"])
    rows = rows[-max(1, min(quarters, 8)):]
    series = [_typed(r) for r in rows]
    first, last = series[0], series[-1]
    return {
        "region_id": region_id.upper(),
        "latest": last,
        "history": series,
        "trend": {
            "unemployment_change_pts": round(last["unemployment_rate_pct"] - first["unemployment_rate_pct"], 2),
            "income_change_pct": round(
                (last["median_household_income_usd"] / first["median_household_income_usd"] - 1) * 100, 2),
        },
    }


@mcp.tool()
def get_prev_credit_history(applicant_id: str) -> dict:
    """Get an applicant's previous credit history: credit score, open accounts,
    utilization, delinquencies in last 24 months, bankruptcies, hard inquiries,
    average account age, existing debt and collections."""
    rows = _find("credit_history.csv", applicant_id)
    if not rows:
        return {"error": f"No credit history found for applicant '{applicant_id}'"}
    return _typed(rows[0])


@mcp.tool()
def get_historic_bank_balance(applicant_id: str, months: int = 12) -> dict:
    """Get monthly historic bank balances for an applicant (avg daily balance, min
    balance, inflow, outflow, overdrafts, NSF flags) for the last `months` (1-12),
    plus a summary: average balance, average net cash flow, balance volatility,
    total overdrafts and NSF months."""
    rows = _find("bank_balances.csv", applicant_id)
    if not rows:
        return {"error": f"No bank data found for applicant '{applicant_id}'"}
    rows.sort(key=lambda r: r["month"])
    series = [_typed(r) for r in rows[-max(1, min(months, 12)):]]
    bals = [r["avg_daily_balance_usd"] for r in series]
    net = [r["total_inflow_usd"] - r["total_outflow_usd"] for r in series]
    return {
        "applicant_id": applicant_id.upper(),
        "months": series,
        "summary": {
            "months_covered": len(series),
            "avg_balance_usd": round(statistics.mean(bals), 2),
            "min_balance_usd": round(min(r["min_balance_usd"] for r in series), 2),
            "avg_monthly_net_cash_flow_usd": round(statistics.mean(net), 2),
            "balance_volatility_usd": round(statistics.pstdev(bals), 2) if len(bals) > 1 else 0.0,
            "total_overdrafts": sum(r["overdraft_count"] for r in series),
            "nsf_months": sum(r["nsf_flag"] for r in series),
        },
    }


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.run(transport="streamable-http")
    else:
        mcp.run()  # stdio; never print to stdout here
