"""Data ingestion from multiple sources. Every loader returns normalised Documents.

Live sources (NewsAPI, GDELT) are optional; bundled sample files keep the demo reproducible offline.
"""
from __future__ import annotations

import hashlib
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path
from typing import List

from .schema import Document


def _id(prefix: str, text: str) -> str:
    return f"{prefix}-{hashlib.md5(text.encode()).hexdigest()[:8]}"


# ---------------------------------------------------------------- offline files
def load_news_file(path: str) -> List[Document]:
    """JSON list of {id?, title, description?, publishedAt, source?, url?} (NewsAPI-like)."""
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Document(
            doc_id=i.get("id") or _id("news", i["title"]),
            source="news",
            text=(i["title"] + ". " + (i.get("description") or "")).strip(),
            timestamp=i["publishedAt"],
            author=i.get("source", ""),
            url=i.get("url", ""),
        )
        for i in items
    ]


def load_tweets_file(path: str) -> List[Document]:
    """JSON list of {id?, text, created_at, user?, retweets?, likes?} (Twitter/X-like)."""
    items = json.loads(Path(path).read_text(encoding="utf-8"))
    return [
        Document(
            doc_id=i.get("id") or _id("tw", i["text"]),
            source="twitter",
            text=i["text"],
            timestamp=i["created_at"],
            author=i.get("user", ""),
            engagement=int(i.get("retweets", 0)) + int(i.get("likes", 0)) // 5,
        )
        for i in items
    ]


# ------------------------------------------------------------------ live feeds
def fetch_newsapi(query: str = "bank OR markets OR sanctions OR default", page_size: int = 30) -> List[Document]:
    """Requires env NEWSAPI_KEY (free tier at newsapi.org)."""
    key = os.getenv("NEWSAPI_KEY")
    if not key:
        raise RuntimeError("Set NEWSAPI_KEY to use the live NewsAPI source.")
    url = "https://newsapi.org/v2/everything?" + urllib.parse.urlencode(
        {"q": query, "language": "en", "sortBy": "publishedAt", "pageSize": page_size, "apiKey": key})
    with urllib.request.urlopen(url, timeout=20) as r:
        arts = json.load(r).get("articles", [])
    return [
        Document(doc_id=_id("news", a["title"]), source="news",
                 text=f'{a["title"]}. {a.get("description") or ""}'.strip(),
                 timestamp=a["publishedAt"], author=(a.get("source") or {}).get("name", ""),
                 url=a.get("url", ""))
        for a in arts if a.get("title")
    ]


def fetch_gdelt(query: str = "sanctions OR default OR recession", max_records: int = 30, timeout: int = 30) -> List[Document]:
    """GDELT DOC 2.0 API (no key required)."""
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urllib.parse.urlencode(
        {"query": query, "mode": "ArtList", "format": "json", "maxrecords": max_records, "sort": "DateDesc"})
    with urllib.request.urlopen(url, timeout=timeout) as r:
        arts = json.load(r).get("articles", [])
    docs = []
    for a in arts:
        ts = a.get("seendate", "")  # 20261010T120000Z
        iso = f"{ts[:4]}-{ts[4:6]}-{ts[6:8]}T{ts[9:11]}:{ts[11:13]}:{ts[13:15]}Z" if len(ts) >= 15 else ts
        docs.append(Document(doc_id=_id("gdelt", a["url"]), source="gdelt", text=a["title"],
                             timestamp=iso, author=a.get("domain", ""), url=a["url"]))
    return docs
