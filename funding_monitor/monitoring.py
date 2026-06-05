from __future__ import annotations

import hashlib
import os
import re
from datetime import datetime, timedelta, timezone
from typing import Any

from .providers import env_keys, post_json_with_key_rotation
from .records import StartupRecord, parse_date

try:
    import feedparser
except ImportError:  # pragma: no cover
    feedparser = None

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

RSS_FEEDS = [
    ("TechCrunch Funding", "https://techcrunch.com/tag/funding/feed/"),
    ("TechCrunch Startups", "https://techcrunch.com/category/startups/feed/"),
    ("VentureBeat", "https://venturebeat.com/category/business/feed/"),
    ("PR Newswire", "https://www.prnewswire.com/rss/news-releases-list.rss"),
    ("BusinessWire", "https://feed.businesswire.com/rss/home/?rss=G1QFDERJXkJeGVtTWg=="),
]

FUNDING_SITES = [
    "techcrunch.com",
    "businesswire.com",
    "prnewswire.com",
    "globenewswire.com",
    "venturebeat.com",
    "crunchbase.com/news",
]

FUNDING_KEYWORDS = [
    "raises",
    "raised",
    "secures",
    "secured",
    "series a",
    "series b",
    "series c",
    "series d",
    "seed round",
    "seed funding",
    "pre-seed",
    "funding round",
    "million in funding",
    "venture capital",
]


def collect_candidates(days_back: int = 2, *, use_rss: bool = True, use_tavily: bool = False, limit: int = 50) -> list[StartupRecord]:
    records: list[StartupRecord] = []
    if use_rss:
        records.extend(collect_rss_candidates(days_back=days_back, limit=limit))
    if use_tavily:
        records.extend(collect_tavily_candidates(limit=limit))
    return dedupe_records(records)[:limit]


def collect_range_candidates(start_date, end_date, *, use_tavily: bool = True, limit: int = 200) -> list[StartupRecord]:
    if not use_tavily:
        return []
    records: list[StartupRecord] = []
    for query in build_range_queries(start_date, end_date):
        records.extend(search_tavily_candidates(query, limit=min(10, limit)))
        if len(dedupe_records(records)) >= limit:
            break
    return dedupe_records(records)[:limit]


def build_range_queries(start_date, end_date) -> list[str]:
    months: list[tuple[int, int, str]] = []
    cursor = start_date.replace(day=1)
    while cursor <= end_date:
        months.append((cursor.year, cursor.month, cursor.strftime("%B")))
        if cursor.month == 12:
            cursor = cursor.replace(year=cursor.year + 1, month=1)
        else:
            cursor = cursor.replace(month=cursor.month + 1)

    domains = [
        "techcrunch.com",
        "news.crunchbase.com",
        "businesswire.com",
        "prnewswire.com",
        "globenewswire.com",
        "venturebeat.com",
    ]
    queries: list[str] = []
    for year, month, month_name in months:
        month_path = f"{year}/{month:02d}"
        for domain in domains:
            queries.extend(
                [
                    f"site:{domain} {month_name} {year} startup raises funding",
                    f"site:{domain}/{month_path} raises funding startup",
                    f"site:{domain} {month_name} {year} raises \"Series A\"",
                    f"site:{domain} {month_name} {year} raises \"Seed\" funding",
                ]
            )
    queries.extend(
        [
            f"startups raised funding between {start_date.isoformat()} and {end_date.isoformat()}",
            f"recently funded startups {start_date.strftime('%B')} {start_date.year} {end_date.strftime('%B')} {end_date.year}",
        ]
    )
    return queries


def collect_rss_candidates(days_back: int = 2, limit: int = 50) -> list[StartupRecord]:
    if feedparser is None:
        return []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days_back)
    records: list[StartupRecord] = []
    for source, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            text = f"{title} {summary}"
            if not is_funding_text(text):
                continue
            published = None
            if getattr(entry, "published_parsed", None):
                published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published and published < cutoff:
                continue
            amount, funding_round = extract_amount_and_round(text)
            records.append(
                StartupRecord(
                    company_name=extract_company_name(title),
                    announced_date=published.date() if published else None,
                    funding_amount=amount,
                    funding_round=funding_round,
                    source_url=entry.get("link", ""),
                    source_title=title,
                    source_publisher=source,
                    raw=dict(entry),
                )
            )
            if len(records) >= limit:
                return records
    return records


def collect_tavily_candidates(limit: int = 25) -> list[StartupRecord]:
    if requests is None:
        return []
    if not env_keys("TAVILY_API_KEY"):
        return []
    queries = [
        "startup raises Series A funding announcement",
        "startup seed funding announcement",
        "startup raises million funding press release",
        "startup Series B funding announcement",
    ]
    records: list[StartupRecord] = []
    for query in queries:
        payload = {
            "query": query,
            "search_depth": "advanced",
            "include_domains": FUNDING_SITES,
            "include_raw_content": False,
            "include_answer": False,
            "max_results": min(limit, 10),
        }
        try:
            response = post_json_with_key_rotation(
                "https://api.tavily.com/search",
                payload,
                env_base="TAVILY_API_KEY",
                api_key_field="api_key",
                timeout=30,
            )
            if response is None:
                continue
            if not response.ok:
                continue
            for result in response.json().get("results", []):
                title = result.get("title", "")
                content = result.get("content", "")
                text = f"{title} {content}"
                if not is_funding_text(text):
                    continue
                amount, funding_round = extract_amount_and_round(text)
                records.append(
                    StartupRecord(
                        company_name=extract_company_name(title),
                        funding_amount=amount,
                        funding_round=funding_round,
                        source_url=result.get("url", ""),
                        source_title=title,
                        source_publisher=result.get("url", "").split("/")[2] if result.get("url") else "Tavily",
                        raw=result,
                    )
                )
                if len(records) >= limit:
                    return dedupe_records(records)
        except requests.RequestException:
            continue
    return dedupe_records(records)


def search_tavily_candidates(query: str, limit: int = 10) -> list[StartupRecord]:
    if requests is None:
        return []
    if not env_keys("TAVILY_API_KEY"):
        return []
    payload = {
        "query": query,
        "search_depth": "advanced",
        "include_raw_content": False,
        "include_answer": False,
        "max_results": limit,
    }
    try:
        response = post_json_with_key_rotation(
            "https://api.tavily.com/search",
            payload,
            env_base="TAVILY_API_KEY",
            api_key_field="api_key",
            timeout=30,
        )
        if response is None:
            return []
        if not response.ok:
            return []
        records: list[StartupRecord] = []
        for result in response.json().get("results", []):
            title = result.get("title", "")
            content = result.get("content", "")
            text = f"{title} {content}"
            if not is_funding_text(text):
                continue
            amount, funding_round = extract_amount_and_round(text)
            records.append(
                StartupRecord(
                    company_name=extract_company_name(title),
                    announced_date=parse_date(result.get("published_date") or result.get("publishedDate")),
                    funding_amount=amount,
                    funding_round=funding_round,
                    source_url=result.get("url", ""),
                    source_title=title,
                    source_publisher=result.get("url", "").split("/")[2] if result.get("url") else "Tavily",
                    raw={"query": query, **result},
                )
            )
        return records
    except requests.RequestException:
        return []


def is_funding_text(text: str) -> bool:
    lowered = text.lower()
    return any(keyword in lowered for keyword in FUNDING_KEYWORDS)


def extract_amount_and_round(text: str) -> tuple[str, str]:
    amount = ""
    amount_match = re.search(r"\$(\d+(?:\.\d+)?)\s*(billion|million|b|m|mn)\b", text, re.I)
    if amount_match:
        unit = amount_match.group(2).lower()
        suffix = "B" if unit.startswith("b") else "M"
        amount = f"${amount_match.group(1)}{suffix}"

    funding_round = ""
    lowered = text.lower()
    for label in ["series e", "series d", "series c", "series b", "series a", "pre-seed", "seed"]:
        if label in lowered:
            funding_round = label.title().replace("Pre-Seed", "Pre-seed")
            break
    return amount, funding_round


def extract_company_name(title: str) -> str:
    patterns = [
        r"^(.+?)\s+(?:raises|raised|secures|secured|closes|lands|nabs)\b",
        r"^(.+?)\s+announces\b.+?\bfunding\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, title, re.I)
        if match:
            return cleanup_company(match.group(1))
    return cleanup_company(re.split(r"[-:|]", title)[0])


def cleanup_company(value: str) -> str:
    value = re.sub(r"^(exclusive|startup|ai startup|tech startup)\s*:\s*", "", value, flags=re.I)
    if ":" in value:
        prefix, suffix = value.split(":", 1)
        if len(prefix.split()) >= 2 and suffix.strip():
            value = suffix
    value = re.sub(r"\s+", " ", value).strip(" -:|")
    return value[:80]


def dedupe_records(records: list[StartupRecord]) -> list[StartupRecord]:
    seen: set[str] = set()
    deduped: list[StartupRecord] = []
    for record in records:
        key_text = record.source_url or f"{record.company_name}:{record.source_title}"
        key = hashlib.sha1(key_text.encode("utf-8")).hexdigest()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(record)
    return deduped
