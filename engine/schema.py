"""Data contracts shared between the Risk Engine and downstream modules."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Optional

EVENT_TYPES = [
    "Geopolitical",
    "Macroeconomic",
    "Credit Event",
    "Merger/Acquisition",
    "Product Launch",
    "Regulatory",
    "Cyber/Operational",
    "Natural Disaster",
    "Earnings",
    "Other",
]


@dataclass
class Document:
    """A normalised piece of unstructured text from any source."""
    doc_id: str
    source: str            # "news" | "twitter" | "gdelt" ...
    text: str
    timestamp: str         # ISO-8601
    author: str = ""
    engagement: int = 0    # retweets / likes / shares (social only)
    url: str = ""
    title: str = ""        # original headline when the source has one (used for de-duplication)


@dataclass
class RiskSignal:
    """Structured, machine-readable output of the engine."""
    signal_id: str
    doc_id: str
    source: str
    timestamp: str
    headline: str
    sentiment_score: float            # -1.0 .. 1.0
    sentiment_label: str              # Negative | Neutral | Positive
    event_type: str                   # one of EVENT_TYPES
    event_confidence: float           # 0 .. 1
    impact_score: float               # 1 .. 10
    entities: list = field(default_factory=list)   # tickers / company names
    region: Optional[str] = None
    publisher: str = ""                # e.g. "BBC Business" (live feeds)
    url: str = ""                      # link to the original article, when known
    rationale: dict = field(default_factory=dict)  # explainability

    def to_dict(self) -> dict:
        return asdict(self)
