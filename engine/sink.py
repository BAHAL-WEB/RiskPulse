"""Output interfaces: JSONL file sink + tiny HTTP API (stdlib only)."""
from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Iterable

from .nlp import RiskAnalyzer
from .schema import Document, RiskSignal


def write_jsonl(signals: Iterable[RiskSignal], path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for s in signals:
            f.write(json.dumps(s.to_dict()) + "\n")


def read_jsonl(path: str) -> list[dict]:
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def serve(signals_path: str, port: int = 8000) -> None:
    """GET /signals?min_impact=7  |  POST /analyze {"text": "...", "source": "news"}"""
    analyzer = RiskAnalyzer()

    class H(BaseHTTPRequestHandler):
        def _send(self, code, obj):
            body = json.dumps(obj).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path.startswith("/signals"):
                min_impact = 0.0
                if "min_impact=" in self.path:
                    min_impact = float(self.path.split("min_impact=")[1].split("&")[0])
                data = [s for s in read_jsonl(signals_path) if s["impact_score"] >= min_impact]
                return self._send(200, data)
            self._send(404, {"error": "not found"})

        def do_POST(self):
            if self.path != "/analyze":
                return self._send(404, {"error": "not found"})
            payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))) or b"{}")
            doc = Document(doc_id="adhoc", source=payload.get("source", "news"),
                           text=payload.get("text", ""), timestamp=payload.get("timestamp", ""),
                           engagement=int(payload.get("engagement", 0)))
            self._send(200, analyzer.analyze(doc).to_dict())

    print(f"Risk Engine API on http://localhost:{port}  (GET /signals, POST /analyze)")
    HTTPServer(("", port), H).serve_forever()
