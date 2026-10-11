"""End-to-end pipeline:  ingest -> NLP Risk Engine -> signals.jsonl -> Module B stress tests -> dashboard.

Usage
  python run_pipeline.py                         # offline demo on bundled sample data
  python run_pipeline.py --live                  # add live NewsAPI (NEWSAPI_KEY) + GDELT sources
  python run_pipeline.py --threshold 6.5         # change stress-test trigger
  python run_pipeline.py --scenario "Geopolitical" --impact 9 --region Asia    # manual what-if
  python run_pipeline.py --serve                 # expose engine as an HTTP API after the run
"""
import argparse
import json
from pathlib import Path

from engine.ingest import fetch_gdelt, fetch_newsapi, load_news_file, load_tweets_file
from engine.nlp import RiskAnalyzer
from engine.sink import read_jsonl, serve, write_jsonl
from stress.portfolio import load_portfolio
from stress.stress_test import StressTester
from dashboard.build_dashboard import build
from service import Session

ROOT = Path(__file__).parent


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--live", action="store_true", help="also pull live NewsAPI + GDELT")
    ap.add_argument("--finbert", action="store_true", help="use FinBERT sentiment (needs transformers)")
    ap.add_argument("--threshold", type=float, default=7.0, help="impact score above which stress test fires")
    ap.add_argument("--portfolio", default=str(ROOT / "data/sample_portfolio.csv"))
    ap.add_argument("--scenario"); ap.add_argument("--impact", type=float, default=9.0); ap.add_argument("--region")
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "output"))
    a = ap.parse_args()
    out = Path(a.out); out.mkdir(exist_ok=True)

    # 1) Ingest (>= 2 sources)
    docs = load_news_file(str(ROOT / "data/sample_news.json")) + load_tweets_file(str(ROOT / "data/sample_tweets.json"))
    if a.live:
        for name, fn in (("NewsAPI", fetch_newsapi), ("GDELT", fetch_gdelt)):
            try:
                docs += fn(); print(f"[ingest] {name} ok")
            except Exception as e:
                print(f"[ingest] {name} skipped: {e}")
    print(f"[ingest] {len(docs)} documents from {sorted({d.source for d in docs})}")

    # 2) NLP Risk Engine -> structured signals
    signals = RiskAnalyzer(use_finbert=a.finbert).analyze_many(docs)
    write_jsonl(signals, str(out / "signals.jsonl"))
    print(f"[engine] {len(signals)} signals -> output/signals.jsonl")

    # 3) Module B: subscribe to signals, trigger stress tests
    tester = StressTester(load_portfolio(a.portfolio), impact_threshold=a.threshold)
    sig_dicts = read_jsonl(str(out / "signals.jsonl"))
    report = tester.run_from_signals(sig_dicts)
    if a.scenario:   # manual what-if appended as an extra scenario
        manual = tester.run(a.scenario, a.impact, a.region,
                            {"signal_id": "manual", "headline": f"Manual scenario: {a.scenario} (impact {a.impact})",
                             "timestamp": "", "sentiment_score": 0, "corroboration": 1, "sources": ["manual"], "signal_ids": []})
        report["results"].insert(0, manual)
    (out / "stress_results.json").write_text(json.dumps(report, indent=2))

    print(f"\n[stress] portfolio ${report['portfolio_value']:,.0f}M, {len(report['results'])} stress tests (impact > {a.threshold})")
    for r in report["results"]:
        p = r["portfolio"]
        print(f"  {r['event_type']:<18} {str(r['region']):<14} impact {r['impact_score']:>4}  "
              f"P&L {p['pnl']:>9,.1f}M ({p['pnl_pct']:>6.2f}%)  {p['limit_status']}")

    # 4) Dashboard
    state = Session(ROOT).state(a.threshold)       # same shape the live app uses
    if a.scenario:
        state["report"]["results"].insert(0, report["results"][0])
    build(state, str(out / "dashboard.html"))
    print("\n[dashboard] output/dashboard.html  (static snapshot; run `python app.py` for the interactive app)")
    if a.serve:
        serve(str(out / "signals.jsonl"))


if __name__ == "__main__":
    main()
