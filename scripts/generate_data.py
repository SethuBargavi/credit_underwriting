"""Generate deterministic mock data (CSV) for the credit underwriting agent.

Run:  uv run python scripts/generate_data.py
Outputs to ./data:
  applicants.csv, locations.csv, macro_economic.csv,
  credit_history.csv, bank_balances.csv
"""
import csv
import random
from datetime import date
from pathlib import Path

random.seed(42)
DATA = Path(__file__).resolve().parent.parent / "data"
DATA.mkdir(exist_ok=True)

# (city, state, zip, region_id)
CITIES = [
    ("Austin", "TX", "78701", "TX-AUS"),
    ("Dallas", "TX", "75201", "TX-DAL"),
    ("San Francisco", "CA", "94105", "CA-SF"),
    ("Los Angeles", "CA", "90012", "CA-LA"),
    ("New York", "NY", "10001", "NY-NYC"),
    ("Buffalo", "NY", "14202", "NY-BUF"),
    ("Chicago", "IL", "60601", "IL-CHI"),
    ("Detroit", "MI", "48226", "MI-DET"),
    ("Miami", "FL", "33131", "FL-MIA"),
    ("Seattle", "WA", "98101", "WA-SEA"),
]

# Per-region macro baselines: unemployment %, median household income, HPI yoy %, cost-of-living idx
MACRO_BASE = {
    "TX-AUS": (3.6, 86000, 3.1, 104),
    "TX-DAL": (3.9, 78000, 2.8, 98),
    "CA-SF": (4.4, 126000, -0.8, 178),
    "CA-LA": (5.1, 83000, 1.2, 150),
    "NY-NYC": (5.3, 78000, 2.0, 168),
    "NY-BUF": (4.7, 58000, 4.5, 88),
    "IL-CHI": (4.9, 74000, 2.4, 106),
    "MI-DET": (6.2, 52000, 3.8, 84),
    "FL-MIA": (3.2, 66000, 5.2, 120),
    "WA-SEA": (4.0, 112000, 1.5, 152),
}

FIRST = ["Aarav", "Maya", "Liam", "Sofia", "Noah", "Priya", "Ethan", "Olivia", "Marcus",
         "Elena", "Jamal", "Chloe", "Diego", "Hannah", "Kenji", "Amara", "Lucas", "Nina",
         "Omar", "Grace", "Victor", "Zoe", "Raj", "Isla", "Tomas", "Leah", "Samir", "Freya",
         "Andre", "Mei"]
LAST = ["Patel", "Nguyen", "Garcia", "Smith", "Kim", "Johnson", "Rossi", "Okafor", "Silva",
        "Cohen", "Hughes", "Tanaka", "Muller", "Reyes", "Singh", "Brown", "Lopez", "Walker"]
EMPLOYMENT = ["Salaried", "Salaried", "Salaried", "Self-employed", "Contract", "Retired"]
HOUSING = ["Rent", "Own-Mortgage", "Own-Outright"]

# Risk profiles drive consistency across all four tables.
PROFILES = {
    "prime":     dict(score=(760, 835), delinq=(0, 0), util=(0.03, 0.22), bal_mult=(3.0, 6.0), overdraft=(0, 0)),
    "near_prime": dict(score=(670, 759), delinq=(0, 1), util=(0.20, 0.50), bal_mult=(1.5, 3.0), overdraft=(0, 1)),
    "subprime":  dict(score=(560, 669), delinq=(1, 4), util=(0.50, 0.85), bal_mult=(0.4, 1.4), overdraft=(1, 4)),
    "deep_sub":  dict(score=(450, 559), delinq=(3, 8), util=(0.80, 1.00), bal_mult=(0.05, 0.5), overdraft=(3, 9)),
}


def write(name, header, rows):
    with open(DATA / name, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"wrote {name}: {len(rows)} rows")


def months_back(n):
    """First-of-month dates for the last n full months, oldest first."""
    today = date(2026, 11, 1)
    out = []
    y, m = today.year, today.month
    for _ in range(n):
        m -= 1
        if m == 0:
            m, y = 12, y - 1
        out.append(date(y, m, 1))
    return list(reversed(out))


def main():
    applicants, locations, credit, balances = [], [], [], []
    mix = ["prime"] * 9 + ["near_prime"] * 10 + ["subprime"] * 7 + ["deep_sub"] * 4
    random.shuffle(mix)

    for i, profile in enumerate(mix, start=1):
        aid = f"APP{i:04d}"
        p = PROFILES[profile]
        city, state, zipc, region = random.choice(CITIES)
        base_inc = MACRO_BASE[region][1]
        income_factor = {"prime": (0.9, 1.8), "near_prime": (0.7, 1.2),
                         "subprime": (0.5, 0.95), "deep_sub": (0.4, 0.75)}[profile]
        annual_income = round(base_inc * random.uniform(*income_factor), -2)
        emp = random.choice(EMPLOYMENT)
        name = f"{random.choice(FIRST)} {random.choice(LAST)}"
        age = random.randint(23, 68) if emp != "Retired" else random.randint(63, 79)
        req_amt = round(random.uniform(5, 45) * 1000, -2)
        applicants.append([aid, name, age, emp, annual_income, req_amt,
                           random.choice([36, 48, 60]), "personal_loan"])

        locations.append([aid, f"{random.randint(10, 9999)} {random.choice(['Oak', 'Main', 'Elm', 'Pine', 'Lake'])} St",
                          city, state, zipc, region, random.randint(0, 15),
                          random.choice(HOUSING)])

        # --- credit history ---
        score = random.randint(*p["score"])
        n_accts = random.randint(2, 14)
        credit.append([
            aid, score, n_accts, round(random.uniform(*p["util"]), 2),
            random.randint(*p["delinq"]),                                   # delinquencies_24m
            int(profile == "deep_sub" and random.random() < 0.5),            # bankruptcies
            random.randint(0, 2 if profile in ("prime", "near_prime") else 7),  # hard inquiries 12m
            round(random.uniform(1, 25) if profile != "deep_sub" else random.uniform(0.5, 6), 1),  # avg age yrs
            round(annual_income * random.uniform(0.0, 0.25 if profile == "prime" else 0.6), -2),  # existing debt
            random.randint(0, 2) if profile in ("subprime", "deep_sub") else 0,  # collections
        ])

        # --- 12 months of bank balances ---
        monthly_income = annual_income / 12
        avg_bal_target = monthly_income * random.uniform(*p["bal_mult"])
        bal = avg_bal_target
        for d in months_back(12):
            inflow = monthly_income * random.uniform(0.9, 1.1)
            if emp in ("Self-employed", "Contract"):
                inflow = monthly_income * random.uniform(0.5, 1.5)
            spend_ratio = {"prime": 0.7, "near_prime": 0.88, "subprime": 0.98, "deep_sub": 1.04}[profile]
            outflow = inflow * spend_ratio * random.uniform(0.92, 1.08)
            bal = max(-300, bal + (inflow - outflow) + (avg_bal_target - bal) * 0.3)
            od = min(p["overdraft"][1], random.choice(
                range(p["overdraft"][0], p["overdraft"][1] + 1))) if p["overdraft"][1] else 0
            balances.append([aid, d.strftime("%Y-%m"), round(bal, 2), round(bal * random.uniform(0.4, 0.8), 2),
                             round(inflow, 2), round(outflow, 2), od,
                             int(random.random() < (0.02 if profile == "prime" else 0.15) and profile != "prime")])

    write("applicants.csv",
          ["applicant_id", "name", "age", "employment_type", "annual_income_usd",
           "requested_amount_usd", "requested_term_months", "product"], applicants)
    write("locations.csv",
          ["applicant_id", "street", "city", "state", "zip", "region_id",
           "years_at_address", "housing_status"], locations)
    write("credit_history.csv",
          ["applicant_id", "credit_score", "open_accounts", "credit_utilization",
           "delinquencies_24m", "bankruptcies", "hard_inquiries_12m",
           "avg_account_age_years", "existing_debt_usd", "collections"], credit)
    write("bank_balances.csv",
          ["applicant_id", "month", "avg_daily_balance_usd", "min_balance_usd",
           "total_inflow_usd", "total_outflow_usd", "overdraft_count", "nsf_flag"], balances)

    # --- macro: per region, 8 quarters ---
    macro = []
    quarters = ["2025Q1", "2025Q2", "2025Q3", "2025Q4", "2026Q1", "2026Q2", "2026Q3", "2026Q4"]
    for region, (unemp, inc, hpi, col) in MACRO_BASE.items():
        for qi, q in enumerate(quarters):
            macro.append([
                region, q,
                round(unemp + random.uniform(-0.3, 0.3) + qi * 0.03, 2),
                round(inc * (1 + 0.007 * qi), -2),
                round(hpi + random.uniform(-0.6, 0.6), 2),
                round(3.4 - qi * 0.05 + random.uniform(-0.2, 0.2), 2),   # CPI inflation yoy %
                round(random.uniform(0.5, 3.2), 2),                       # regional GDP growth yoy %
                round(random.uniform(1.0, 4.0) + (2.0 if unemp > 5.5 else 0), 2),  # regional delinquency rate %
                col,
                round(4.50 - qi * 0.125, 3),                              # fed funds rate %
            ])
    write("macro_economic.csv",
          ["region_id", "quarter", "unemployment_rate_pct", "median_household_income_usd",
           "home_price_index_yoy_pct", "cpi_inflation_yoy_pct", "gdp_growth_yoy_pct",
           "regional_loan_delinquency_rate_pct", "cost_of_living_index", "fed_funds_rate_pct"], macro)


if __name__ == "__main__":
    main()
