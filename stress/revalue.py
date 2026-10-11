"""Position-level revaluation under a shock. Returns P&L split by risk factor (USD millions).

Methods (deliberately simple, transparent, and standard in first-pass stress testing):
  Equity      : MV x beta x equity shock
  Bond        : duration-convexity approximation for rates + spread-duration for credit
  Loan        : spread mark-down + expected-loss uplift (PD scaled by spread widening x LGD)
  IRS         : DV01-style  notional x duration x dy  (pay-fixed gains when rates rise) + CVA
  FX forward  : notional x FX shock x direction
  Equity opt. : delta-gamma approximation
  Non-USD cash assets also carry FX translation P&L.
"""
from __future__ import annotations

from .portfolio import LGD, PD, Position
from .scenarios import EM_CCY, Scenario

FACTORS = ("rates", "credit", "equity", "fx")


def stressed_pd(pd: float, spread_shock: float) -> float:
    """PD multiplier: +100bp of effective spread widening ~ +50% PD."""
    return min(1.0, pd * (1 + (spread_shock * 1e4 / 100) * 0.5))


def fx_shock(sc: Scenario, ccy: str, severity: float) -> float:
    if ccy == "USD":
        return 0.0
    bucket = "EM" if ccy in EM_CCY else ccy
    return sc.fx.get(bucket, 0.0) / 100 * severity


def revalue(p: Position, sc: Scenario, severity: float, event_region: str | None) -> dict:
    mult = 1.0
    if event_region:
        mult = sc.region_mult if p.region == event_region else sc.off_region_mult
    sm = sc.sector_mult.get(p.sector, 1.0)

    eq = sc.equity_pct / 100 * severity * mult * sm
    dy = sc.rates_bps / 1e4 * severity
    ds = sc.spread_bps / 1e4 * severity * mult * sm
    fx = fx_shock(sc, p.currency, severity)

    pnl = dict.fromkeys(FACTORS, 0.0)
    mv = p.market_value

    if p.asset_type == "Equity":
        pnl["equity"] = mv * p.beta * eq
        pnl["fx"] = mv * fx
    elif p.asset_type == "Bond":
        convexity = 1.1 * p.duration ** 2
        pnl["rates"] = mv * (-p.duration * dy + 0.5 * convexity * dy ** 2)
        if not p.is_govt:
            pnl["credit"] = -mv * p.duration * 0.9 * ds
        pnl["fx"] = mv * fx
    elif p.asset_type == "Loan":
        pd0 = PD.get(p.rating, 0.01)
        el_uplift = p.notional * (stressed_pd(pd0, ds) - pd0) * LGD["Loan"]
        pnl["credit"] = -mv * p.duration * 0.5 * ds - el_uplift
        pnl["fx"] = mv * fx
    elif p.asset_type == "Derivative":
        if p.instrument == "Interest Rate Swap":
            pnl["rates"] = p.direction * p.notional * p.duration * dy
        elif p.instrument == "FX Forward":
            pnl["fx"] = p.direction * p.notional * fx
        elif p.instrument == "Equity Option":
            pnl["equity"] = p.notional * (p.delta * eq + 0.5 * p.gamma * eq ** 2)
        # CVA: loss on counterparty default, only when we are in the money after the shock
        exposure = max(mv + sum(pnl.values()), 0.0)
        pd0 = PD.get(p.rating, 0.01)
        pnl["credit"] -= exposure * (stressed_pd(pd0, ds) - pd0) * LGD["Derivative"]
    return pnl
