from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html import unescape
from typing import Iterable
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from .providers import env_keys
from .records import StartupRecord, parse_date

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from bs4 import BeautifulSoup
except ImportError:  # pragma: no cover
    BeautifulSoup = None

PLACEHOLDER_MARKERS = ("...", "[...]", "http://...", "https://...")
GENERIC_COMPANY_NAMES = {
    "ai",
    "the",
    "a",
    "an",
    "fm",
    "software",
    "startup",
    "company",
    "app",
    "platform",
}
MONTH_NAMES = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
}
TRACKING_PARAMS = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid"}


def verify_records(
    records: list[StartupRecord],
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    fetch_articles: bool = False,
    allow_url_date_fallback: bool = False,
    use_apify: bool = False,
    max_apify_runs: int = 0,
    fetch_timeout: int = 8,
    max_workers: int = 1,
    html_by_url: dict[str, str] | None = None,
) -> list[StartupRecord]:
    html_by_url = html_by_url or {}

    if fetch_articles and max_workers > 1 and not use_apify:
        def work(record: StartupRecord) -> StartupRecord:
            return verify_record(
                record,
                start_date,
                end_date,
                fetch_articles=fetch_articles,
                allow_url_date_fallback=allow_url_date_fallback,
                fetcher=ArticleFetcher(fetch_timeout=fetch_timeout),
                html_by_url=html_by_url,
            )

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            return list(executor.map(work, records))

    fetcher = ArticleFetcher(use_apify=use_apify, max_apify_runs=max_apify_runs, fetch_timeout=fetch_timeout)
    return [
        verify_record(
            record,
            start_date,
            end_date,
            fetch_articles=fetch_articles,
            allow_url_date_fallback=allow_url_date_fallback,
            fetcher=fetcher,
            html_by_url=html_by_url,
        )
        for record in records
    ]


def verify_record(
    record: StartupRecord,
    start_date: date | None = None,
    end_date: date | None = None,
    *,
    fetch_articles: bool = False,
    allow_url_date_fallback: bool = False,
    fetcher: "ArticleFetcher | None" = None,
    html_by_url: dict[str, str] | None = None,
) -> StartupRecord:
    record.notes = list(record.notes)
    record.source_url = normalize_url(record.source_url)
    record.company_name = normalize_company_name(record.company_name)

    if company_name_is_invalid(record.company_name):
        reject(record, "invalid_company_name")
        return record

    if not record.source_url or has_placeholder_url(record.source_url):
        reject(record, "invalid_source_url")
        return record

    url_date = extract_date_from_url(record.source_url)
    if url_date and start_date and end_date and not (start_date <= url_date <= end_date):
        record.article_published_date = url_date
        reject(record, "article_date_outside_target_window")
        return record

    if is_probable_aggregate_or_fund_source(record):
        reject(record, "not_startup_funding_article")
        return record

    if funding_amount_is_implausible(record.funding_amount):
        reject(record, "implausible_funding_amount")
        return record

    if funding_amount_is_valuation(record):
        record.notes.append("funding_amount_looked_like_valuation")
        record.funding_amount = ""

    html = (html_by_url or {}).get(record.source_url, "")
    if fetch_articles and not html:
        html = (fetcher or ArticleFetcher()).fetch(record.source_url)

    article_date = None
    if html:
        article_date = extract_article_date(html)
        record.source_title = record.source_title or extract_title(html)
        record.website = record.website or extract_company_website(record.company_name, html, record.source_url)
        if not company_appears_in_article(record.company_name, html):
            reject(record, "identity_conflict")
            return record

    if not article_date:
        article_date = url_date
        if article_date and not allow_url_date_fallback:
            record.notes.append("date_only_found_in_url")

    if not article_date:
        review(record, "article_date_missing")
        return record

    record.article_published_date = article_date
    record.article_date_verified = bool(html) or allow_url_date_fallback

    if start_date and end_date and not (start_date <= article_date <= end_date):
        reject(record, "article_date_outside_target_window")
        return record

    if is_probable_aggregate_or_fund_source(record):
        reject(record, "not_startup_funding_article")
        return record

    if not is_specific_startup_funding_article(record):
        reject(record, "not_startup_funding_article")
        return record

    if not html and allow_url_date_fallback and not company_context_matches_source(record):
        reject(record, "identity_conflict")
        return record

    if not record.article_date_verified:
        review(record, "article_not_crawled")
        return record

    record.funding_round = infer_round_from_source(record) or record.funding_round
    record.verification_status = "verified"
    record.confidence = max(record.confidence, 80 if html else 65)
    return record


class ArticleFetcher:
    def __init__(self, *, use_apify: bool = False, max_apify_runs: int = 0, fetch_timeout: int = 8) -> None:
        self.use_apify = use_apify
        self.max_apify_runs = max(0, max_apify_runs)
        self.apify_runs = 0
        self.fetch_timeout = fetch_timeout

    def fetch(self, url: str) -> str:
        html = fetch_article_html(url, timeout=self.fetch_timeout)
        if html:
            return html
        if not self.use_apify or self.apify_runs >= self.max_apify_runs:
            return ""
        self.apify_runs += 1
        return fetch_article_html_with_apify(url)


def reject(record: StartupRecord, reason: str) -> None:
    record.verification_status = f"rejected_{reason}"
    record.confidence = min(record.confidence, 25)
    if reason not in record.notes:
        record.notes.append(reason)


def review(record: StartupRecord, reason: str) -> None:
    record.verification_status = f"needs_review_{reason}"
    record.confidence = min(record.confidence or 50, 55)
    if reason not in record.notes:
        record.notes.append(reason)


def normalize_url(url: str) -> str:
    text = unescape(str(url or "").strip())
    if has_placeholder_url(text):
        return text
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return text
    query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True) if key not in TRACKING_PARAMS]
    return urlunparse(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            urlencode(query),
            "",
        )
    )


def has_placeholder_url(url: str) -> bool:
    text = str(url or "").strip()
    return not text or any(marker in text for marker in PLACEHOLDER_MARKERS)


def fetch_article_html(url: str, timeout: int = 30) -> str:
    if requests is None:
        return ""
    headers = {
        "User-Agent": "recently-funded-startup-monitor/0.1 (+https://github.com/)",
        "Accept": "text/html,application/xhtml+xml",
    }
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        if response.ok and "text/html" in response.headers.get("content-type", "").lower():
            return response.text
    except requests.RequestException:
        return ""
    return ""


def fetch_article_html_with_apify(url: str) -> str:
    tokens = env_keys("APIFY_API_TOKEN")
    if not tokens:
        return ""
    actor_id = os.environ.get("APIFY_ARTICLE_ACTOR_ID", "apify/website-content-crawler")
    try:
        from apify_client import ApifyClient
    except ImportError:
        return ""

    for token in tokens:
        try:
            client = ApifyClient(token)
            run_input = {
                "startUrls": [{"url": url}],
                "maxCrawlPages": 1,
                "maxConcurrency": 1,
            }
            run = client.actor(actor_id).call(run_input=run_input)
            dataset_id = run.get("defaultDatasetId")
            if not dataset_id:
                continue
            for item in client.dataset(dataset_id).iterate_items():
                for key in ("html", "text", "markdown", "content", "pageText"):
                    value = item.get(key)
                    if value:
                        return str(value)
        except Exception:
            continue
    return ""


def extract_article_date(html: str) -> date | None:
    if not html:
        return None
    if BeautifulSoup is None:
        return extract_date_from_text(html)

    soup = BeautifulSoup(html, "html.parser")
    meta_names = [
        ("property", "article:published_time"),
        ("property", "og:published_time"),
        ("name", "date"),
        ("name", "dc.date"),
        ("name", "dcterms.date"),
        ("name", "publishdate"),
        ("name", "pubdate"),
        ("name", "datepublished"),
        ("itemprop", "datePublished"),
    ]
    for attr, value in meta_names:
        node = soup.find("meta", attrs={attr: re.compile(f"^{re.escape(value)}$", re.I)})
        parsed = parse_date(node.get("content")) if node and node.get("content") else None
        if parsed:
            return parsed

    for script in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        parsed = extract_json_ld_date(script.string or script.get_text(" ", strip=True))
        if parsed:
            return parsed

    for node in soup.find_all("time"):
        parsed = parse_date(node.get("datetime") or node.get_text(" ", strip=True))
        if parsed:
            return parsed

    return extract_date_from_text(soup.get_text(" ", strip=True))


def extract_json_ld_date(text: str) -> date | None:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None

    def walk(value: object) -> Iterable[object]:
        if isinstance(value, dict):
            yield value
            for child in value.values():
                yield from walk(child)
        elif isinstance(value, list):
            for item in value:
                yield from walk(item)

    for item in walk(payload):
        if isinstance(item, dict):
            parsed = parse_date(item.get("datePublished") or item.get("dateCreated") or item.get("dateModified"))
            if parsed:
                return parsed
    return None


def extract_date_from_text(text: str) -> date | None:
    patterns = [
        r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b",
        r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(20\d{2})\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.I)
        if not match:
            continue
        if len(match.groups()) == 3 and match.group(1).isdigit():
            return parse_date("-".join(match.groups()))
        return parse_date(match.group(0))
    return None


def extract_date_from_url(url: str) -> date | None:
    parsed = urlparse(url)
    path = parsed.path
    patterns = [
        r"/(20\d{2})/(\d{1,2})/(\d{1,2})(?:/|$)",
        r"/(20\d{2})-(\d{1,2})-(\d{1,2})(?:-|/|$)",
        r"-(20\d{2})(\d{2})(\d{2})(?:-|/|$)",
        r"/home/(20\d{2})(\d{2})(\d{2})\d*/",
    ]
    for pattern in patterns:
        match = re.search(pattern, path)
        if match:
            groups = match.groups()
            if len(groups[1]) == 2 and len(groups[2]) == 2:
                return parse_date(f"{groups[0]}-{groups[1]}-{groups[2]}")
    return None


def extract_title(html: str) -> str:
    if BeautifulSoup is None:
        match = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
        return re.sub(r"\s+", " ", match.group(1)).strip() if match else ""
    soup = BeautifulSoup(html, "html.parser")
    if soup.title:
        return soup.title.get_text(" ", strip=True)
    return ""


def company_appears_in_article(company_name: str, html: str) -> bool:
    text = re.sub(r"\s+", " ", html).lower()
    company = company_name.strip().lower()
    if company in text:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", company) if len(token) > 2]
    return bool(tokens) and all(token in text for token in tokens[:2])


def company_name_is_invalid(company_name: str) -> bool:
    name = str(company_name or "").strip()
    lowered = name.lower()
    if not name or lowered in GENERIC_COMPANY_NAMES or lowered in MONTH_NAMES:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", lowered) if token]
    if len(tokens) > 5:
        return True
    if lowered.endswith(" has"):
        return True
    invalid_markers = [
        "startup",
        "funding",
        "venture",
        "series",
        "what it takes",
        "how ",
        "every ",
        "learn ",
        "sources say",
        "seeks fresh",
    ]
    return any(marker in lowered for marker in invalid_markers)


def normalize_company_name(company_name: str) -> str:
    name = re.sub(r"\s+", " ", str(company_name or "").strip())
    if ":" in name:
        prefix, suffix = name.split(":", 1)
        if len(prefix.split()) >= 2 and suffix.strip():
            name = suffix.strip()
    return name


def company_context_matches_source(record: StartupRecord) -> bool:
    context = f"{record.source_url} {record.source_title}".lower()
    company = record.company_name.strip().lower()
    if company and company in context:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", company) if len(token) > 2]
    return bool(tokens) and any(token in context for token in tokens)


def extract_company_website(company_name: str, html: str, source_url: str) -> str:
    if BeautifulSoup is None:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    source_domain = urlparse(source_url).netloc.lower().removeprefix("www.")
    for link in soup.find_all("a", href=True):
        href = urljoin(source_url, str(link.get("href") or "").strip())
        if is_probable_company_domain(company_name, href, source_domain):
            return normalize_url(href)
    return ""


def is_probable_company_domain(company_name: str, url: str, source_domain: str = "") -> bool:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return False
    domain = parsed.netloc.lower().removeprefix("www.")
    if source_domain and (domain == source_domain or domain.endswith("." + source_domain)):
        return False
    blocked_domains = [
        "techcrunch.com",
        "prnewswire.com",
        "globenewswire.com",
        "businesswire.com",
        "crunchbase.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "youtube.com",
        "sec.gov",
    ]
    if any(blocked in domain for blocked in blocked_domains):
        return False
    domain_compact = domain.replace("-", "").replace(".", "")
    company_compact = re.sub(r"[^a-z0-9]+", "", company_name.lower())
    if company_compact and len(company_compact) >= 2 and company_compact in domain_compact:
        return True
    tokens = [token for token in re.split(r"[^a-z0-9]+", company_name.lower()) if len(token) >= 4]
    return bool(tokens) and any(token in domain_compact for token in tokens)


def is_probable_aggregate_or_fund_source(record: StartupRecord) -> bool:
    context = f"{record.source_url} {record.source_title}".lower()
    aggregate_markers = [
        "biggest-funding-rounds",
        "startup-funding-shatters",
        "funding-shatters-all-records",
        "every-fusion-startup",
        "every fusion startup",
        "venture-funds",
        "venture fund",
        "venture firm",
        "venture-firm",
        "new-venture-funds",
        "for-new-funds",
        "fund-to-back",
        "fund to back",
        "growth-stage-funds",
        "what-it-takes-to-raise",
        "learn-what-it-takes",
        "live-only-at-techcrunch-disrupt",
        "disrupt-2026",
        "seeks-fresh-funding",
        "valuation-sources-say",
        "valuation-vc-funding",
        "across-three-startups",
        "across three startups",
        "raised-more-than",
        "raises-1-billion-for-new-venture",
    ]
    return any(marker in context for marker in aggregate_markers)


def is_specific_startup_funding_article(record: StartupRecord) -> bool:
    context = f"{record.source_url} {record.source_title}".lower()
    action_markers = [
        "raises",
        "raised",
        "secures",
        "secured",
        "announces",
        "announced",
        "closes",
        "closed",
        "lands",
        "nabs",
        "bags",
        "scores",
    ]
    if not any(marker in context for marker in action_markers):
        return False
    if record.funding_amount or record.funding_round:
        return True
    return bool(re.search(r"\$\d+(?:\.\d+)?\s*(?:m|million|b|billion)\b", context, re.I))


def infer_round_from_source(record: StartupRecord) -> str:
    context = f"{record.source_url} {record.source_title}".lower().replace("-", " ")
    for label in ["series e", "series d", "series c", "series b", "series a", "pre seed", "seed"]:
        if label in context:
            return label.title().replace("Pre Seed", "Pre-seed")
    return ""


def funding_amount_is_implausible(amount: str) -> bool:
    match = re.search(r"\$(\d+(?:\.\d+)?)([bm])\b", str(amount or ""), re.I)
    if not match:
        return False
    value = float(match.group(1))
    unit = match.group(2).upper()
    return unit == "B" and value > 25


def funding_amount_is_valuation(record: StartupRecord) -> bool:
    if not record.funding_amount:
        return False
    context = f"{record.source_url} {record.source_title}".lower()
    amount = record.funding_amount.lower().replace("$", "").replace(".0", "")
    compact_context = context.replace("%24", "$").replace("-", " ")
    valuation_patterns = [
        rf"{re.escape(amount)}m valuation",
        rf"{re.escape(amount)}b valuation",
        " valuation",
    ]
    return "valuation" in compact_context and not re.search(rf"(?:raises|raised|secures|secured)\s+\${re.escape(amount)}", compact_context)


def date_window_from_days(days_back: int) -> tuple[date, date]:
    end = datetime.now(timezone.utc).date()
    return end - timedelta(days=days_back), end
