"""Live headline extraction from news channels via public RSS/Atom feeds (stdlib only, no API key).

Feeds are listed in data/feeds.json. Each feed is fetched in parallel; a failing feed is skipped and
reported, so one broken URL never stops the run.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import List, Tuple

from .schema import Document

UA = "Mozilla/5.0 (compatible; RiskPulse/1.0; +https://github.com/)"
_TAG = re.compile(r"<[^>]+>")


def _clean(s: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(_TAG.sub(" ", s or ""))).strip()


def _iso(raw: str | None) -> str:
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
        except (TypeError, ValueError):
            try:
                dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                dt = None
        if dt is not None:
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_feed(xml_bytes: bytes, feed_name: str, limit: int = 25) -> List[Document]:
    """Parse RSS 2.0 or Atom into Documents."""
    root = ET.fromstring(xml_bytes)
    docs: List[Document] = []
    for item in root.iter():
        if _local(item.tag) not in ("item", "entry"):
            continue
        f = {}
        for child in item:
            k = _local(child.tag)
            if k == "link":
                f["link"] = child.get("href") or (child.text or "")
            elif k not in f:
                f[k] = child.text
        title = _clean(f.get("title"))
        if not title:
            continue
        desc = _clean(f.get("description") or f.get("summary") or "")
        if desc.lower().startswith(title.lower()[:40]):
            desc = ""
        link = (f.get("link") or "").strip()
        docs.append(Document(
            doc_id="live-" + hashlib.md5((link or title).encode()).hexdigest()[:10],
            source="news", text=(title + ". " + desc[:300]).strip() if desc else title,
            timestamp=_iso(f.get("pubDate") or f.get("published") or f.get("updated") or f.get("date")),
            author=feed_name, url=link, title=title))
        if len(docs) >= limit:
            break
    return docs


def load_feed_config(path: str) -> list[dict]:
    cfg = json.loads(Path(path).read_text(encoding="utf-8"))
    return [f for f in cfg.get("feeds", []) if f.get("enabled", True)]


def _fetch_one(feed: dict, limit: int, timeout: int) -> Tuple[dict, List[Document], str | None]:
    try:
        req = urllib.request.Request(feed["url"], headers={"User-Agent": UA, "Accept": "application/rss+xml, application/xml, text/xml, */*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            docs = parse_feed(r.read(), feed["name"], limit)
        return feed, docs, None
    except Exception as exc:
        return feed, [], f"{type(exc).__name__}: {str(exc)[:90]}"


def fetch_live_headlines(config_path: str, per_feed: int = 20, timeout: int = 10) -> Tuple[List[Document], list[dict]]:
    """Fetch all enabled feeds. Returns (deduplicated documents, per-feed status list)."""
    feeds = load_feed_config(config_path)
    with ThreadPoolExecutor(max_workers=min(8, max(1, len(feeds)))) as ex:
        results = list(ex.map(lambda f: _fetch_one(f, per_feed, timeout), feeds))
    seen, docs, status = set(), [], []
    for feed, got, err in results:
        status.append({"name": feed["name"], "ok": err is None, "count": len(got), "error": err})
        for d in got:
            key = re.sub(r"\W+", "", (d.title or d.text).lower())[:80]
            if key not in seen:
                seen.add(key); docs.append(d)
    docs.sort(key=lambda d: d.timestamp, reverse=True)
    return docs, status
