"""Application service: holds the working set of documents and computes signals + stress tests.

Used by app.py (interactive web app). Keeps run_pipeline.py's logic in one reusable place.
"""
from __future__ import annotations

import threading
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import json

from engine.ingest import fetch_gdelt, load_news_file, load_tweets_file
from engine.live import fetch_live_headlines
from engine.nlp import RiskAnalyzer
from engine.schema import EVENT_TYPES, Document
from stress.portfolio import load_portfolio
from stress.stress_test import StressTester

REGIONS = ["North America", "Europe", "Asia", "India", "Middle East", "Latin America", "Africa"]


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class Session:
    def __init__(self, root: str | Path, feeds_path: str | None = None):
        self.root = Path(root)
        self.feeds_path = feeds_path or str(self.root / "data/feeds.json")
        self.analyzer = RiskAnalyzer()
        self.portfolio = load_portfolio(str(self.root / "data/sample_portfolio.csv"))
        self.sample_docs = (load_news_file(str(self.root / "data/sample_news.json"))
                            + load_tweets_file(str(self.root / "data/sample_tweets.json")))
        self.lock = threading.Lock()
        self.mode, self.docs, self.custom, self.feed_status = "sample", list(self.sample_docs), [], []
        self.updated = _now()

    # ------------------------------------------------------------------ data sources
    def load_sample(self) -> None:
        with self.lock:
            self.mode, self.docs, self.feed_status, self.updated = "sample", list(self.sample_docs), [], _now()

    def load_live(self) -> list[dict]:
        """Pull live headlines: RSS feeds from news channels + GDELT (both free, no key)."""
        docs, status = fetch_live_headlines(self.feeds_path)
        try:
            g = json.loads(Path(self.feeds_path).read_text(encoding="utf-8")).get("gdelt", {})
        except Exception:
            g = {}
        if g.get("enabled"):
            try:
                gd = fetch_gdelt(g.get("query", "(sanctions OR default OR recession)"), 25, timeout=10)
                status.append({"name": "GDELT", "ok": True, "count": len(gd), "error": None})
                seen = {d.text.lower()[:50] for d in docs}
                docs += [d for d in gd if d.text.lower()[:50] not in seen]
            except Exception as exc:
                status.append({"name": "GDELT", "ok": False, "count": 0, "error": f"{type(exc).__name__}: {str(exc)[:90]}"})
        with self.lock:
            self.feed_status = status
            if docs:   # if every source failed, keep whatever was showing before
                # Live mode shows live text only. Bundled sample tweets are old, so they are left out
                # (social posts need a paid API; paste your own posts in "Analyze your own").
                self.mode, self.docs, self.updated = "live", sorted(docs, key=lambda d: d.timestamp, reverse=True), _now()
        return status

    def add_custom(self, text: str, source: str = "news", engagement: int = 0) -> str:
        doc = Document(doc_id=f"mine-{len(self.custom)+1}", source=source if source in ("news", "twitter") else "news",
                       text=text.strip(), timestamp=_now(), author="you", engagement=engagement)
        with self.lock:
            self.custom.append(doc)
        return f"sig-{doc.doc_id}"

    def clear_custom(self) -> None:
        with self.lock:
            self.custom = []

    # ------------------------------------------------------------------------ outputs
    def _portfolio_summary(self) -> dict:
        by = defaultdict(lambda: {"count": 0, "value": 0.0})
        for p in self.portfolio:
            by[p.asset_type]["count"] += 1
            by[p.asset_type]["value"] += p.market_value
        return {"n_positions": len(self.portfolio), "value": round(sum(p.market_value for p in self.portfolio), 1),
                "by_asset_type": [{"name": k, "count": v["count"], "value": round(v["value"], 1)} for k, v in by.items()]}

    def state(self, threshold: float = 7.0) -> dict:
        with self.lock:
            docs = list(self.docs) + list(self.custom)
            mode, updated, feeds = self.mode, self.updated, list(self.feed_status)
        signals = [s.to_dict() for s in self.analyzer.analyze_many(docs)]
        report = StressTester(self.portfolio, threshold).run_from_signals(signals)
        return {"mode": mode, "updated": updated, "feeds": feeds, "threshold": threshold, "n_custom": len(self.custom),
                "signals": signals, "report": report, "portfolio": self._portfolio_summary(),
                "options": {"event_types": [e for e in EVENT_TYPES], "regions": REGIONS}}

    def analyze_text(self, text: str, source: str = "news", engagement: int = 0) -> dict:
        doc = Document("adhoc", source if source in ("news", "twitter") else "news", text, _now(), engagement=engagement)
        return self.analyzer.analyze(doc).to_dict()

    def what_if(self, event_type: str, impact: float, region: str | None, threshold: float = 7.0,
                headline: str | None = None) -> dict:
        tester = StressTester(self.portfolio, threshold)
        trig = {"signal_id": "manual", "headline": headline or f"What-if: {event_type}" + (f" in {region}" if region else ""),
                "timestamp": "", "sentiment_score": 0, "corroboration": 1, "sources": ["what-if"], "signal_ids": []}
        return tester.run(event_type, max(0.0, min(10.0, impact)), region or None, trig)
