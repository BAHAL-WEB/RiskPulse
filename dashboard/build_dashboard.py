"""Builds a static, self-contained dashboard.html snapshot (no server needed).

For the full interactive app (live headlines, analyze your own text, what-if) run:  python app.py
"""
import json
from pathlib import Path

TEMPLATE = Path(__file__).with_name("app.html")


def build(state: dict, path: str) -> None:
    payload = json.dumps(state).replace("</", "<\\/")
    Path(path).write_text(TEMPLATE.read_text(encoding="utf-8").replace("__DATA__", payload), encoding="utf-8")
