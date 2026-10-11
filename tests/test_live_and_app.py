import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

from engine.live import fetch_live_headlines, parse_feed
from service import Session

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Fed raises rates by 75 bps &amp; warns of recession</title><description>&lt;p&gt;Markets tumble.&lt;/p&gt;</description>
<link>https://x.com/a</link><pubDate>Sat, 10 Oct 2026 14:00:00 GMT</pubDate></item>
<item><title>Fed raises rates by 75 bps &amp; warns of recession</title><link>https://x.com/dup</link></item></channel></rss>"""
ATOM = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Oil jumps on Hormuz tensions</title>
<link href="https://y.com/b"/><updated>2026-10-10T12:00:00Z</updated><summary>Brent up 5%</summary></entry></feed>"""
ROOT = Path(__file__).resolve().parent.parent


class LiveFeedTests(unittest.TestCase):
    def test_parse_rss_strips_html_and_parses_time(self):
        d = parse_feed(RSS, "T")[0]
        self.assertIn("&", d.text); self.assertNotIn("<p>", d.text)
        self.assertEqual(d.timestamp, "2026-10-10T14:00:00Z"); self.assertEqual(d.url, "https://x.com/a")

    def test_parse_atom(self):
        d = parse_feed(ATOM, "T")[0]
        self.assertEqual(d.url, "https://y.com/b"); self.assertEqual(d.timestamp, "2026-10-10T12:00:00Z")

    def test_fetch_dedupes_and_survives_a_broken_feed(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / "a.xml").write_bytes(RSS); (Path(t) / "b.xml").write_bytes(ATOM)
            cfg = {"feeds": [{"name": "A", "url": (Path(t) / "a.xml").as_uri()}, {"name": "B", "url": (Path(t) / "b.xml").as_uri()},
                             {"name": "Broken", "url": (Path(t) / "missing.xml").as_uri()},
                             {"name": "Off", "url": "http://invalid.invalid/x", "enabled": False}]}
            (Path(t) / "feeds.json").write_text(json.dumps(cfg))
            docs, status = fetch_live_headlines(str(Path(t) / "feeds.json"))
        self.assertEqual(len(docs), 2)                              # duplicate title merged
        self.assertEqual({s["name"]: s["ok"] for s in status}, {"A": True, "B": True, "Broken": False})


class ServiceAndApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from app import make_handler
        cls.session = Session(ROOT)
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(cls.session))
        cls.port = cls.server.server_address[1]
        threading.Thread(target=cls.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def call(self, path, body=None):
        req = urllib.request.Request(f"http://127.0.0.1:{self.port}{path}", data=None if body is None else json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as r:
                return r.status, json.load(r)
        except urllib.error.HTTPError as e:
            return e.code, json.load(e)

    def test_state_shape_and_threshold(self):
        _, hi = self.call("/api/state?threshold=7"); _, lo = self.call("/api/state?threshold=5")
        self.assertEqual(hi["mode"], "sample"); self.assertEqual(len(hi["signals"]), 23)
        self.assertGreaterEqual(len(lo["report"]["results"]), len(hi["report"]["results"]))
        for k in ("portfolio", "options", "feeds", "report"):
            self.assertIn(k, hi)

    def test_page_is_served(self):
        with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/") as r:
            html = r.read().decode()
        self.assertIn("RiskPulse", html); self.assertNotIn("__DATA__", html)

    def test_analyze_validates_and_scores(self):
        code, out = self.call("/api/analyze", {"text": "hi"}); self.assertEqual(code, 400)
        code, out = self.call("/api/analyze", {"text": "Bank defaults on bonds, creditors seek restructuring", "source": "news"})
        self.assertEqual(code, 200); self.assertEqual(out["signal"]["event_type"], "Credit Event")

    def test_whatif_and_custom_headline(self):
        _, r = self.call("/api/whatif", {"event_type": "Macroeconomic", "impact": 8, "region": "North America"})
        self.assertLess(r["portfolio"]["pnl"], 0)
        self.call("/api/analyze", {"text": "Massive ransomware attack halts payments at banks", "add": True})
        _, st = self.call("/api/state?threshold=7"); self.assertEqual(st["n_custom"], 1)
        _, st = self.call("/api/sample", {}); self.assertEqual(st["n_custom"], 0)


if __name__ == "__main__":
    unittest.main()
