from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from typing import Any


def parse_date(value: Any) -> date | None:
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()

    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    candidates = [
        text,
        text[:10],
        text.replace("/", "-"),
    ]
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate).date()
        except ValueError:
            pass

    for fmt in ("%m/%d/%Y", "%d/%m/%Y", "%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def format_date(value: date | None) -> str:
    return value.isoformat() if value else ""


@dataclass
class FounderProfile:
    name: str = ""
    role: str = ""
    linkedin_url: str = ""
    evidence: list[str] = field(default_factory=list)
    confidence: int = 0
    status: str = "needs_review"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StartupRecord:
    company_name: str
    announced_date: date | None = None
    funding_amount: str = ""
    funding_round: str = ""
    website: str = ""
    source_url: str = ""
    source_title: str = ""
    source_publisher: str = ""
    article_published_date: date | None = None
    article_date_verified: bool = False
    investors: list[str] = field(default_factory=list)
    founders: list[FounderProfile] = field(default_factory=list)
    verification_status: str = "needs_review"
    confidence: int = 0
    notes: list[str] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)

    def key(self) -> tuple[str, str, str]:
        return (
            self.company_name.strip().lower(),
            format_date(self.announced_date),
            self.source_url.strip().lower(),
        )

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["announced_date"] = format_date(self.announced_date)
        data["article_published_date"] = format_date(self.article_published_date)
        data["founders"] = [founder.to_dict() for founder in self.founders]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StartupRecord":
        founders = [
            founder if isinstance(founder, FounderProfile) else FounderProfile(**founder)
            for founder in data.get("founders", []) or []
        ]
        return cls(
            company_name=str(data.get("company_name") or data.get("company") or data.get("startup") or "").strip(),
            announced_date=parse_date(data.get("announced_date") or data.get("date") or data.get("published")),
            funding_amount=str(data.get("funding_amount") or data.get("amount") or "").strip(),
            funding_round=str(data.get("funding_round") or data.get("round") or data.get("round_type") or "").strip(),
            website=str(data.get("website") or data.get("company_website") or "").strip(),
            source_url=str(data.get("source_url") or data.get("url") or data.get("article") or "").strip(),
            source_title=str(data.get("source_title") or data.get("title") or "").strip(),
            source_publisher=str(data.get("source_publisher") or data.get("source") or "").strip(),
            article_published_date=parse_date(data.get("article_published_date")),
            article_date_verified=bool(data.get("article_date_verified", False)),
            investors=list(data.get("investors") or []),
            founders=founders,
            verification_status=str(data.get("verification_status") or data.get("status") or "needs_review"),
            confidence=int(data.get("confidence") or 0),
            notes=list(data.get("notes") or []),
            raw=dict(data.get("raw") or data),
        )
