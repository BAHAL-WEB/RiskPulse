"""Portfolio model + loaders. Values are USD millions."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from typing import List

# Through-the-cycle one-year probability of default by rating (used for loan / counterparty credit loss).
PD = {"AAA": 0.0002, "AA": 0.0005, "A": 0.001, "BBB": 0.004, "BB": 0.02, "B": 0.065, "CCC": 0.18, "NR": 0.01}
LGD = {"Loan": 0.45, "Bond": 0.60, "Derivative": 0.60}


@dataclass
class Position:
    trade_id: str
    asset_type: str       # Loan | Bond | Derivative | Equity
    instrument: str
    counterparty: str
    sector: str
    region: str
    currency: str
    notional: float
    market_value: float
    rating: str
    duration: float
    direction: int        # +1 pay-fixed/long, -1 receive-fixed/short (derivatives)
    delta: float
    gamma: float
    beta: float

    @property
    def is_govt(self) -> bool:
        return self.sector == "Government"


def load_portfolio(path: str) -> List[Position]:
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out.append(Position(
                trade_id=r["trade_id"], asset_type=r["asset_type"], instrument=r["instrument"],
                counterparty=r["counterparty"], sector=r["sector"], region=r["region"],
                currency=r["currency"], notional=float(r["notional"]), market_value=float(r["market_value"]),
                rating=r["rating"], duration=float(r["duration"]), direction=int(float(r["direction"])),
                delta=float(r["delta"]), gamma=float(r["gamma"]), beta=float(r["beta"])))
    return out


def from_transactions(csv_path: str, amount_col: str = "amount", category_col: str = "category",
                      region: str = "Europe", currency: str = "GBP") -> List[Position]:
    """Adapter: turn a retail/SME transaction file (Salad Money, Kaggle Financial Transactions...)
    into loan exposures by spending category, so real transaction data can seed the book.
    Each category's total outflow becomes one term-loan position to a 'category' counterparty.
    """
    totals: dict[str, float] = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            try:
                totals[r[category_col]] = totals.get(r[category_col], 0.0) + abs(float(r[amount_col]))
            except (ValueError, KeyError):
                continue
    scale = 1e-6  # raw units -> millions
    return [Position(trade_id=f"TX{i+1:04d}", asset_type="Loan", instrument="Term Loan", counterparty=cat,
                     sector="Consumer", region=region, currency=currency, notional=round(v * scale, 2),
                     market_value=round(v * scale * 0.99, 2), rating="BBB", duration=3.0, direction=1,
                     delta=0, gamma=0, beta=0) for i, (cat, v) in enumerate(sorted(totals.items()))]
