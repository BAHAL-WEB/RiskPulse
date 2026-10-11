"""Shock library: event class -> market shocks at full severity (Impact Score = 10).

Applied shocks scale linearly with the engine's Impact Score, so a 10 hits at 100% of the
table and an 8 hits at 80%. Region multipliers concentrate the shock where the news happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

EM_CCY = {"INR", "BRL", "ZAR", "TRY", "MXN"}


@dataclass
class Scenario:
    name: str
    description: str
    equity_pct: float            # % move in equity prices
    rates_bps: float             # parallel move in risk-free yields
    spread_bps: float            # corporate credit spread widening
    fx: dict = field(default_factory=dict)             # ccy bucket -> % vs USD (EM / EUR / GBP / JPY / CHF)
    sector_mult: dict = field(default_factory=dict)    # sector -> multiplier on equity & spread shocks
    region_mult: float = 1.4     # multiplier for assets in the event's region
    off_region_mult: float = 0.8


SCENARIOS = {
    "Geopolitical": Scenario(
        "Geopolitical shock", "Risk-off: equities sell off, flight to quality compresses yields, EM FX weakens.",
        equity_pct=-15, rates_bps=-50, spread_bps=110,
        fx={"EM": -7, "EUR": -2, "GBP": -2, "JPY": 3, "CHF": 2},
        sector_mult={"Energy": 0.5, "Industrials": 1.2, "Technology": 1.3, "Financials": 1.1}),
    "Macroeconomic": Scenario(
        "Macro / rate shock", "Surprise tightening: yields jump, equities de-rate, spreads widen.",
        equity_pct=-10, rates_bps=125, spread_bps=70,
        fx={"EM": -5, "EUR": -1.5, "GBP": -1.5, "JPY": -1.5},
        sector_mult={"Real Estate": 1.6, "Technology": 1.3, "Utilities": 1.2, "Financials": 0.8}),
    "Credit Event": Scenario(
        "Credit event / contagion", "Counterparty default triggers spread blow-out and funding stress.",
        equity_pct=-12, rates_bps=-25, spread_bps=180,
        fx={"EM": -4, "EUR": -2},
        sector_mult={"Financials": 1.7, "Real Estate": 1.3}),
    "Cyber/Operational": Scenario(
        "Cyber / operational outage", "Systemic outage hits banks and payments; confidence shock.",
        equity_pct=-8, rates_bps=-10, spread_bps=60, fx={},
        sector_mult={"Financials": 1.6, "Technology": 1.4}),
    "Natural Disaster": Scenario(
        "Natural disaster", "Localised physical damage and supply-chain disruption.",
        equity_pct=-7, rates_bps=-5, spread_bps=80, fx={"JPY": 1},
        sector_mult={"Industrials": 1.5, "Technology": 1.3, "Real Estate": 1.4}, region_mult=2.0, off_region_mult=0.4),
    "Regulatory": Scenario(
        "Regulatory crackdown", "Enforcement action and compliance cost repricing.",
        equity_pct=-6, rates_bps=0, spread_bps=40, fx={}, sector_mult={"Financials": 1.3, "Technology": 1.3}),
    "Merger/Acquisition": Scenario(
        "M&A repricing", "Deal-related spread and equity repricing; limited systemic impact.",
        equity_pct=-3, rates_bps=0, spread_bps=20, fx={}, sector_mult={}),
    "Earnings": Scenario(
        "Earnings shock", "Single-name / sector earnings miss.",
        equity_pct=-4, rates_bps=0, spread_bps=25, fx={}, sector_mult={}),
    "Product Launch": Scenario(
        "Product launch", "Negligible systemic impact.", equity_pct=-1, rates_bps=0, spread_bps=0, fx={}),
    "Other": Scenario("Other", "Uncategorised event; minimal shock.", equity_pct=-1, rates_bps=0, spread_bps=5, fx={}),
}


def get_scenario(event_type: str) -> Scenario:
    return SCENARIOS.get(event_type, SCENARIOS["Other"])
