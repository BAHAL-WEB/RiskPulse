import unittest

from engine.ingest import load_news_file, load_tweets_file
from engine.nlp import RiskAnalyzer
from engine.schema import Document, EVENT_TYPES
from stress.portfolio import load_portfolio
from stress.stress_test import StressTester

A = RiskAnalyzer()


def doc(text, source="news", engagement=0):
    return Document("x", source, text, "2026-10-10T00:00:00Z", engagement=engagement)


class EngineTests(unittest.TestCase):
    def test_sentiment_direction_and_bounds(self):
        pos = A.sentiment("Company beats estimates with record profit and strong growth")
        neg = A.sentiment("Bank defaults, shares plunge amid fraud probe and crisis fears")
        self.assertGreater(pos, 0.3); self.assertLess(neg, -0.3)
        for s in (pos, neg, A.sentiment("")):
            self.assertTrue(-1.0 <= s <= 1.0)

    def test_negation(self):
        self.assertGreater(A.sentiment("The outlook is not weak"), A.sentiment("The outlook is weak"))

    def test_event_classification(self):
        cases = {
            "Troops cross the border as sanctions and missile strikes escalate": "Geopolitical",
            "Fed announces surprise rate hike as inflation surges": "Macroeconomic",
            "Lender files for bankruptcy after bond default": "Credit Event",
            "Firm to acquire rival in $5 billion merger deal": "Merger/Acquisition",
            "Company unveils new product and launches platform": "Product Launch",
        }
        for text, expected in cases.items():
            self.assertEqual(A.analyze(doc(text)).event_type, expected, text)

    def test_impact_ordering_and_range(self):
        severe = A.analyze(doc("Invasion triggers war, global sanctions and market crash"))
        mild = A.analyze(doc("Company unveils new app feature"))
        self.assertGreater(severe.impact_score, 7); self.assertLess(mild.impact_score, 5)
        self.assertTrue(1 <= mild.impact_score <= severe.impact_score <= 10)

    def test_output_schema(self):
        s = A.analyze(doc("Apple unveils new iPhone, shares rally")).to_dict()
        for k in ("sentiment_score", "event_type", "impact_score", "entities", "region", "rationale"):
            self.assertIn(k, s)
        self.assertIn(s["event_type"], EVENT_TYPES); self.assertIn("AAPL", s["entities"])

    def test_two_sources_ingested(self):
        docs = load_news_file("data/sample_news.json") + load_tweets_file("data/sample_tweets.json")
        self.assertEqual({d.source for d in docs}, {"news", "twitter"})


class StressTests(unittest.TestCase):
    def setUp(self):
        self.t = StressTester(load_portfolio("data/sample_portfolio.csv"), 7.0)

    def test_value_reconciles(self):
        r = self.t.run("Geopolitical", 9, "Asia")["portfolio"]
        self.assertAlmostEqual(r["before"] + r["pnl"], r["after"], places=2)

    def test_attribution_sums_to_pnl(self):
        r = self.t.run("Credit Event", 8, "Europe")
        self.assertAlmostEqual(sum(r["attribution"].values()), r["portfolio"]["pnl"], delta=0.01)

    def test_loss_scales_with_impact(self):
        lo = self.t.run("Macroeconomic", 5)["portfolio"]["pnl"]; hi = self.t.run("Macroeconomic", 10)["portfolio"]["pnl"]
        self.assertLess(hi, lo); self.assertLess(lo, 0)

    def test_zero_impact_is_noop(self):
        self.assertAlmostEqual(self.t.run("Geopolitical", 0)["portfolio"]["pnl"], 0, places=6)

    def test_trigger_threshold_and_grouping(self):
        sig = lambda i, imp, ev="Geopolitical", reg="Asia", src="news": dict(
            signal_id=i, impact_score=imp, event_type=ev, region=reg, source=src)
        groups = self.t.triggered([sig("a", 9), sig("b", 8, src="twitter"), sig("c", 7.0), sig("d", 6.9, "Credit Event", "Europe")])
        self.assertEqual(len(groups), 1)                          # 7.0 is not > 7; 6.9 below
        self.assertEqual(groups[0]["lead"]["signal_id"], "a")
        self.assertEqual(groups[0]["sources"], ["news", "twitter"])

    def test_rate_hike_hurts_bonds(self):
        r = self.t.run("Macroeconomic", 10)
        self.assertLess(next(x for x in r["by_asset_type"] if x["name"] == "Bond")["pnl"], 0)
        self.assertEqual(set(r["attribution"]), {"rates", "credit", "equity", "fx"})

    def test_pay_fixed_swap_gains_when_rates_rise(self):
        from stress.portfolio import Position
        from stress.revalue import revalue
        from stress.scenarios import get_scenario
        swap = lambda d: Position("S", "Derivative", "Interest Rate Swap", "CP", "Financials", "North America",
                                  "USD", 100, 0, "AA", 5, d, 0, 0, 0)
        sc = get_scenario("Macroeconomic")   # +125bp at full severity
        self.assertGreater(revalue(swap(1), sc, 1.0, None)["rates"], 0)
        self.assertLess(revalue(swap(-1), sc, 1.0, None)["rates"], 0)


if __name__ == "__main__":
    unittest.main()
