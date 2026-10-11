"""RiskPulse interactive web app.

    python app.py                 # opens http://localhost:8000 in your browser
    python app.py --live          # fetch live headlines on start
    python app.py --port 9000 --no-browser

Endpoints (used by the UI, also handy for scripting):
    GET  /api/state?threshold=7        signals + stress tests for the current data
    POST /api/live                     pull live headlines from the RSS feeds in data/feeds.json
    POST /api/sample                   go back to the bundled sample data
    POST /api/analyze  {text, source}  score one headline (optionally add it to the feed with "add": true)
    POST /api/whatif   {event_type, impact, region}   run a manual scenario
"""
import argparse
import json
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from service import Session

ROOT = Path(__file__).parent
PAGE = ROOT / "dashboard" / "app.html"


def make_handler(session: Session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # keep the console quiet
            pass

        def _json(self, obj, code=200):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _body(self) -> dict:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}") if n else {}

        def do_GET(self):
            u = urlparse(self.path)
            if u.path in ("/", "/index.html"):
                html = PAGE.read_text(encoding="utf-8").replace("__DATA__", "null").encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(html)))
                self.end_headers()
                self.wfile.write(html)
            elif u.path == "/api/state":
                q = parse_qs(u.query)
                self._json(session.state(float(q.get("threshold", ["7"])[0])))
            else:
                self._json({"error": "not found"}, 404)

        def do_POST(self):
            try:
                b, path = self._body(), urlparse(self.path).path
                th = float(b.get("threshold", 7))
                if path == "/api/live":
                    status = session.load_live()
                    ok = sum(1 for s in status if s["ok"])
                    out = session.state(th)
                    out["live_ok"] = ok > 0
                    out["live_message"] = (f"Loaded headlines from {ok} of {len(status)} news feeds." if ok else
                                           "Could not reach any news feed. Check your internet connection. Showing previous data.")
                    self._json(out)
                elif path == "/api/sample":
                    session.load_sample(); session.clear_custom(); self._json(session.state(th))
                elif path == "/api/analyze":
                    text = (b.get("text") or "").strip()
                    if len(text) < 8:
                        return self._json({"error": "Please enter a headline or a few words of text."}, 400)
                    src, eng = b.get("source", "news"), int(b.get("engagement", 0))
                    sig = session.analyze_text(text, src, eng)
                    if b.get("add"):
                        session.add_custom(text, src, eng)
                    self._json({"signal": sig})
                elif path == "/api/whatif":
                    self._json(session.what_if(b.get("event_type", "Geopolitical"), float(b.get("impact", 8)),
                                               b.get("region") or None, th, b.get("headline")))
                else:
                    self._json({"error": "not found"}, 404)
            except Exception as exc:
                self._json({"error": f"{type(exc).__name__}: {exc}"}, 500)

    return Handler


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--live", action="store_true", help="fetch live headlines on start")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--feeds", help="path to a feeds.json (default data/feeds.json)")
    a = ap.parse_args()
    session = Session(ROOT, a.feeds)
    if a.live:
        print("Fetching live headlines ...")
        ok = sum(1 for s in session.load_live() if s["ok"])
        print(f"  {ok} feed(s) loaded" if ok else "  no feed reachable, starting with sample data")
    server = ThreadingHTTPServer(("127.0.0.1", a.port), make_handler(session))
    url = f"http://localhost:{a.port}"
    print(f"RiskPulse running at {url}  (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")


if __name__ == "__main__":
    main()
