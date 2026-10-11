"""Module B: event-driven stress testing engine.

Subscribes to the Risk Engine's signals (Event Classification + Impact Score), triggers a
stress test when Impact > threshold, and reports portfolio value before/after.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Iterable, List

from .portfolio import Position
from .revalue import FACTORS, revalue
from .scenarios import get_scenario

WARN_LIMIT = -0.025    # P&L / portfolio value
BREACH_LIMIT = -0.05


def _round(x: float) -> float:
    return round(x, 3)


class StressTester:
    def __init__(self, portfolio: List[Position], impact_threshold: float = 7.0):
        self.portfolio = portfolio
        self.threshold = impact_threshold
        self.base_value = sum(p.market_value for p in portfolio)

    # ----------------------------------------------------------------- single run
    def run(self, event_type: str, impact: float, region: str | None = None, trigger: dict | None = None) -> dict:
        sc = get_scenario(event_type)
        severity = max(0.0, min(impact, 10.0)) / 10.0

        by_type, by_sector, by_region = (defaultdict(lambda: {"before": 0.0, "pnl": 0.0}) for _ in range(3))
        attribution = dict.fromkeys(FACTORS, 0.0)
        positions = []
        for p in self.portfolio:
            pnl = revalue(p, sc, severity, region)
            total = sum(pnl.values())
            for k, v in pnl.items():
                attribution[k] += v
            for bucket, key in ((by_type, p.asset_type), (by_sector, p.sector), (by_region, p.region)):
                bucket[key]["before"] += p.market_value
                bucket[key]["pnl"] += total
            positions.append({"trade_id": p.trade_id, "asset_type": p.asset_type, "instrument": p.instrument,
                              "counterparty": p.counterparty, "sector": p.sector, "region": p.region,
                              "before": _round(p.market_value), "after": _round(p.market_value + total),
                              "pnl": _round(total), "pnl_pct": _round(100 * total / p.market_value) if p.market_value else 0})

        pnl_total = sum(attribution.values())
        pct = pnl_total / self.base_value
        status = "BREACH" if pct <= BREACH_LIMIT else "WARNING" if pct <= WARN_LIMIT else "WITHIN LIMITS"

        def fmt(d):
            return [{"name": k, "before": _round(v["before"]), "after": _round(v["before"] + v["pnl"]),
                     "pnl": _round(v["pnl"])} for k, v in sorted(d.items(), key=lambda kv: kv[1]["pnl"])]

        return {
            "event_type": event_type,
            "region": region,
            "impact_score": impact,
            "severity": round(severity, 2),
            "scenario": {"name": sc.name, "description": sc.description,
                         "applied_shocks": {
                             "equity_pct": round(sc.equity_pct * severity, 2),
                             "rates_bps": round(sc.rates_bps * severity, 1),
                             "spread_bps": round(sc.spread_bps * severity, 1),
                             "fx_pct": {k: round(v * severity, 2) for k, v in sc.fx.items()}}},
            "trigger": trigger,
            "portfolio": {"before": _round(self.base_value), "after": _round(self.base_value + pnl_total),
                          "pnl": _round(pnl_total), "pnl_pct": round(100 * pct, 2),
                          "limit_status": status, "warn_limit_pct": WARN_LIMIT * 100, "breach_limit_pct": BREACH_LIMIT * 100},
            "attribution": {k: _round(v) for k, v in attribution.items()},
            "by_asset_type": fmt(by_type), "by_sector": fmt(by_sector), "by_region": fmt(by_region),
            "top_losers": sorted(positions, key=lambda x: x["pnl"])[:10],
            "top_gainers": sorted(positions, key=lambda x: -x["pnl"])[:5],
        }

    # -------------------------------------------------------- signal subscription
    def triggered(self, signals: Iterable[dict]) -> List[dict]:
        """Group high-impact signals by (event_type, region); keep the worst per group and
        record corroborating signals/sources so multi-source confirmation is visible."""
        groups: dict = defaultdict(list)
        for s in signals:
            if s["impact_score"] > self.threshold and s["event_type"] != "Other":
                groups[(s["event_type"], s["region"])].append(s)
        out = []
        for (ev, region), sigs in groups.items():
            lead = max(sigs, key=lambda s: s["impact_score"])
            out.append({"lead": lead, "corroboration": len(sigs),
                        "sources": sorted({s["source"] for s in sigs}),
                        "signal_ids": [s["signal_id"] for s in sigs]})
        return sorted(out, key=lambda g: -g["lead"]["impact_score"])

    def run_from_signals(self, signals: List[dict]) -> dict:
        results = []
        for g in self.triggered(signals):
            lead = g["lead"]
            trig = {"signal_id": lead["signal_id"], "headline": lead["headline"], "timestamp": lead["timestamp"],
                    "sentiment_score": lead["sentiment_score"], "corroboration": g["corroboration"],
                    "sources": g["sources"], "signal_ids": g["signal_ids"]}
            results.append(self.run(lead["event_type"], lead["impact_score"], lead["region"], trig))
        combined = sum(r["portfolio"]["pnl"] for r in results)
        return {
            "threshold": self.threshold,
            "portfolio_value": _round(self.base_value),
            "n_positions": len(self.portfolio),
            "results": results,
            "combined_additive_pnl": _round(combined),
            "combined_additive_pnl_pct": round(100 * combined / self.base_value, 2),
        }
