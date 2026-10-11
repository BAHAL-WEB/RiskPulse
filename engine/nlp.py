"""NLP core: sentiment, event classification, impact scoring, entity/region tagging.

Default pipeline is a transparent, dependency-free hybrid (finance lexicon + rules),
so the whole project runs offline and every score is explainable. If `transformers`
is installed, pass use_finbert=True to swap the sentiment model for ProsusAI/finbert.
"""
from __future__ import annotations

import math
import re
from typing import Iterable, Optional

from .lexicons import (BASE_IMPACT, COMPANIES, EVENT_RULES, INTENSIFIERS, NEGATIVE,
                       NEGATORS, POSITIVE, REGIONS, SEVERITY_TERMS)
from .schema import Document, RiskSignal

_TOKEN = re.compile(r"[a-zA-Z][a-zA-Z\-']+")
_MONEY = re.compile(r"\$\s?(\d+(?:\.\d+)?)\s?(trillion|billion|bn|million|m)?", re.I)
_PERCENT = re.compile(r"(\d+(?:\.\d+)?)\s?%")

# Credibility prior: how much we trust each source type for impact scoring.
SOURCE_WEIGHT = {"news": 1.0, "gdelt": 0.9, "twitter": 0.7}


class RiskAnalyzer:
    def __init__(self, use_finbert: bool = False):
        self._finbert = None
        if use_finbert:
            try:  # optional dependency
                from transformers import pipeline
                self._finbert = pipeline("text-classification", model="ProsusAI/finbert", top_k=None)
            except Exception as exc:  # pragma: no cover
                print(f"[engine] FinBERT unavailable ({exc}); using lexicon sentiment.")
        self._event_patterns = {
            ev: [(re.compile(p, re.I), w) for p, w in rules.items()]
            for ev, rules in EVENT_RULES.items()
        }
        self._severity = [(re.compile(p, re.I), w) for p, w in SEVERITY_TERMS.items()]
        self._regions = {r: [re.compile(p, re.I) for p in ps] for r, ps in REGIONS.items()}

    # ---------------------------------------------------------------- sentiment
    def sentiment(self, text: str) -> float:
        """Return a score in [-1, 1]."""
        if self._finbert is not None:  # pragma: no cover
            out = {d["label"].lower(): d["score"] for d in self._finbert(text[:512])[0]}
            return round(out.get("positive", 0) - out.get("negative", 0), 3)

        tokens = [t.lower() for t in _TOKEN.findall(text)]
        total, hits = 0.0, 0
        for i, tok in enumerate(tokens):
            val = POSITIVE.get(tok, 0) or NEGATIVE.get(tok, 0)
            if not val:
                continue
            window = tokens[max(0, i - 3):i]
            if any(w in NEGATORS for w in window):
                val = -val * 0.8            # "not weak" -> mildly positive
            for w in window:
                val *= INTENSIFIERS.get(w, 1.0)
            total += val
            hits += 1
        if hits == 0:
            return 0.0
        # tanh squashes to (-1, 1); the sqrt(hits) term lets stronger evidence saturate.
        return round(math.tanh(total / (4.0 + 0.5 * math.sqrt(hits))), 3)

    @staticmethod
    def label(score: float) -> str:
        return "Positive" if score >= 0.15 else "Negative" if score <= -0.15 else "Neutral"

    # ------------------------------------------------------------ classification
    def classify_event(self, text: str) -> tuple[str, float, dict]:
        scores = {}
        for ev, patterns in self._event_patterns.items():
            s = 0.0
            for rx, w in patterns:
                s += w * min(len(rx.findall(text)), 3)   # cap repeats
            if s:
                scores[ev] = s
        if not scores:
            return "Other", 0.3, {}
        best = max(scores, key=scores.get)
        confidence = scores[best] / (sum(scores.values()) + 1.0)
        return best, round(min(confidence + 0.15, 0.99), 2), scores

    # -------------------------------------------------------------------- impact
    def impact(self, text: str, event: str, sentiment: float, doc: Optional[Document] = None) -> tuple[float, dict]:
        base = BASE_IMPACT.get(event, 2.0)
        # Negative news moves markets more than positive news of the same magnitude.
        sent_adj = 2.5 * abs(sentiment) if sentiment < 0 else 0.8 * abs(sentiment)
        sev = sum(w * min(len(rx.findall(text)), 2) for rx, w in self._severity)
        sev = min(sev, 2.5)

        size = 0.0   # magnitude cues: "$40 billion", "12%"
        for m in _MONEY.finditer(text):
            amt = float(m.group(1))
            unit = (m.group(2) or "").lower()
            usd = amt * {"trillion": 1e12, "billion": 1e9, "bn": 1e9, "million": 1e6, "m": 1e6}.get(unit, 1)
            if usd >= 1e9:
                size = max(size, min(1.0, 0.4 + 0.2 * math.log10(usd / 1e9 + 1)))
        for m in _PERCENT.finditer(text):
            size = max(size, min(0.8, float(m.group(1)) / 25))

        src_w, reach = 1.0, 0.0
        if doc is not None:
            src_w = SOURCE_WEIGHT.get(doc.source, 0.8)
            if doc.engagement:  # viral social posts get a bump
                reach = min(0.8, math.log10(doc.engagement + 1) / 6)

        raw = base + sent_adj + sev + size + reach
        # Calm, routine news (rate holds, small moves) is not market-moving: damp toward the low end.
        if sent_adj + sev + size + reach < 1.0:
            raw = base * 0.8
        # Low-credibility sources pull the score toward the base rather than amplify it.
        score = base + (raw - base) * src_w
        score = max(1.0, min(10.0, score))
        return round(score, 1), {
            "base": base, "sentiment_adj": round(sent_adj, 2), "severity_terms": round(sev, 2),
            "magnitude": round(size, 2), "reach": round(reach, 2), "source_weight": src_w,
        }

    # ------------------------------------------------------------------ entities
    @staticmethod
    def entities(text: str) -> list[str]:
        found = [t for name, t in COMPANIES.items() if re.search(rf"\b{re.escape(name)}\b", text)]
        found += re.findall(r"\$([A-Z]{1,5})\b", text)           # cashtags
        return sorted(set(found))

    def region(self, text: str) -> Optional[str]:
        counts = {r: sum(len(p.findall(text)) for p in ps) for r, ps in self._regions.items()}
        counts = {r: c for r, c in counts.items() if c}
        return max(counts, key=counts.get) if counts else None

    @staticmethod
    def headline(text: str) -> str:
        """First sentence, trimmed on a word boundary (news text is 'title. description')."""
        first = re.split(r"(?<=[.!?])\s+", text.strip().split("\n")[0], maxsplit=1)[0]
        if len(first) <= 140:
            return first
        return first[:140].rsplit(" ", 1)[0] + "…"

    # --------------------------------------------------------------------- main
    def analyze(self, doc: Document) -> RiskSignal:
        text = doc.text
        sent = self.sentiment(text)
        event, conf, ev_scores = self.classify_event(text)
        impact, why = self.impact(text, event, sent, doc)
        why["event_scores"] = {k: round(v, 2) for k, v in sorted(ev_scores.items(), key=lambda kv: -kv[1])[:3]}
        return RiskSignal(
            signal_id=f"sig-{doc.doc_id}",
            doc_id=doc.doc_id,
            source=doc.source,
            timestamp=doc.timestamp,
            headline=self.headline(text),
            sentiment_score=sent,
            sentiment_label=self.label(sent),
            event_type=event,
            event_confidence=conf,
            impact_score=impact,
            entities=self.entities(text),
            region=self.region(text),
            publisher=doc.author,
            url=doc.url,
            rationale=why,
        )

    def analyze_many(self, docs: Iterable[Document]) -> list[RiskSignal]:
        return sorted((self.analyze(d) for d in docs), key=lambda s: s.timestamp)
