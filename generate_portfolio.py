"""Generate a synthetic wholesale-banking book (loans, bonds, derivatives, equities).

Schema mirrors what you would get after mapping a transaction dataset (e.g. Salad Money / Kaggle
Financial Transactions) onto trade-level exposures; see stress/portfolio.py::from_transactions.
Run:  python generate_portfolio.py
"""
import csv
import random

random.seed(42)
SECTORS = ["Financials", "Technology", "Energy", "Industrials", "Consumer", "Healthcare", "Real Estate", "Utilities"]
REGIONS = ["North America", "Europe", "Asia", "India", "Middle East", "Latin America"]
CCY = {"North America": "USD", "Europe": "EUR", "Asia": "JPY", "India": "INR", "Middle East": "USD", "Latin America": "BRL"}
RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B"]
NAMES = ["Atlas", "Borealis", "Cobalt", "Dunmore", "Everline", "Fulcrum", "Granite", "Helios", "Ironvale",
         "Juniper", "Kestrel", "Lumen", "Meridian", "Northwind", "Orion", "Pinnacle", "Quanta", "Redwood",
         "Sterling", "Titan", "Umbra", "Vertex", "Wexford", "Zenith"]

rows = []
def add(**kw):
    rows.append({"trade_id": f"T{len(rows)+1:04d}", **kw})

def cp(): return random.choice(NAMES) + " " + random.choice(["Holdings", "Capital", "Industries", "Group", "Partners"])

for _ in range(24):   # loans
    r = random.choice(REGIONS); n = round(random.uniform(20, 150), 1)
    add(asset_type="Loan", instrument=random.choice(["Term Loan", "Revolver", "Syndicated Loan"]), counterparty=cp(),
        sector=random.choice(SECTORS), region=r, currency=CCY[r], notional=n, market_value=round(n * random.uniform(.97, 1.0), 1),
        rating=random.choice(RATINGS[2:]), duration=round(random.uniform(1, 4), 2), direction=1, delta=0, gamma=0, beta=0)
for _ in range(18):   # bonds
    r = random.choice(REGIONS); n = round(random.uniform(30, 200), 1); govt = random.random() < .3
    add(asset_type="Bond", instrument="Government Bond" if govt else "Corporate Bond", counterparty="Sovereign" if govt else cp(),
        sector="Government" if govt else random.choice(SECTORS), region=r, currency=CCY[r], notional=n,
        market_value=round(n * random.uniform(.93, 1.04), 1), rating="AA" if govt else random.choice(RATINGS[1:]),
        duration=round(random.uniform(2, 12), 2), direction=1, delta=0, gamma=0, beta=0)
for _ in range(10):   # interest-rate swaps
    r = random.choice(REGIONS[:3]); n = round(random.uniform(100, 400), 1)
    add(asset_type="Derivative", instrument="Interest Rate Swap", counterparty=cp(), sector="Financials", region=r, currency=CCY[r],
        notional=n, market_value=round(random.uniform(-3, 6), 1), rating=random.choice(RATINGS[:4]),
        duration=round(random.uniform(3, 8), 2), direction=random.choice([1, -1]), delta=0, gamma=0, beta=0)
for _ in range(5):    # FX forwards
    r = random.choice(["Europe", "Asia", "India", "Latin America"]); n = round(random.uniform(50, 200), 1)
    add(asset_type="Derivative", instrument="FX Forward", counterparty=cp(), sector="Financials", region=r, currency=CCY[r],
        notional=n, market_value=round(random.uniform(-2, 3), 1), rating=random.choice(RATINGS[:4]), duration=0.5,
        direction=random.choice([1, -1]), delta=0, gamma=0, beta=0)
for _ in range(5):    # equity options
    r = random.choice(REGIONS[:3]); n = round(random.uniform(30, 120), 1)
    add(asset_type="Derivative", instrument="Equity Option", counterparty=cp(), sector=random.choice(SECTORS), region=r,
        currency=CCY[r], notional=n, market_value=round(n * random.uniform(.03, .09), 1), rating=random.choice(RATINGS[:4]),
        duration=0.5, direction=1, delta=round(random.uniform(.3, .7), 2), gamma=round(random.uniform(.5, 2.0), 2), beta=1.0)
for _ in range(14):   # equities / trading book
    r = random.choice(REGIONS); n = round(random.uniform(5, 40), 1)
    add(asset_type="Equity", instrument="Common Stock", counterparty="Market", sector=random.choice(SECTORS), region=r,
        currency=CCY[r], notional=n, market_value=n, rating="NR", duration=0, direction=1, delta=1, gamma=0,
        beta=round(random.uniform(.7, 1.5), 2))

with open("data/sample_portfolio.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
print(f"wrote {len(rows)} positions -> data/sample_portfolio.csv (values in USD millions)")
