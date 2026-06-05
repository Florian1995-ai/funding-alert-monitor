from __future__ import annotations

import re
from urllib.parse import urlparse

from .providers import env_keys, post_json_with_key_rotation
from .records import FounderProfile, StartupRecord

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

FOUNDER_ROLE_RE = re.compile(r"\b(co[- ]?founder|founder|chief executive|ceo|president|owner)\b", re.I)


def validate_founders(records: list[StartupRecord]) -> list[StartupRecord]:
    for record in records:
        seen: set[tuple[str, str]] = set()
        clean_founders: list[FounderProfile] = []
        for founder in record.founders:
            founder.name = normalize_person_name(founder.name)
            founder.linkedin_url = normalize_linkedin_url(founder.linkedin_url)
            key = (founder.name.lower(), founder.linkedin_url.lower())
            if key in seen:
                continue
            seen.add(key)

            signals = identity_signals(record, founder)
            founder.evidence = sorted(set(founder.evidence + signals))
            founder.confidence = max(founder.confidence, founder_confidence(signals))
            is_quarantined_candidate = founder.status.startswith(
                ("needs_review_search_candidate", "needs_review_seed_import")
            )
            if is_quarantined_candidate:
                if founder.status.startswith("needs_review_seed_import"):
                    founder.evidence.append("seed_import_requires_reverification")
                founder.status = "needs_review_search_candidate"
                founder.confidence = min(founder.confidence, 55)
            elif len(signals) >= 2:
                founder.status = "verified"
            elif founder.linkedin_url and founder.name and FOUNDER_ROLE_RE.search(founder.role or ""):
                founder.status = "needs_review_single_signal"
            else:
                founder.status = "needs_review_identity"
            clean_founders.append(founder)
        record.founders = clean_founders
    return records


def enrich_founders_with_search(
    records: list[StartupRecord],
    *,
    use_tavily: bool = False,
    use_exa: bool = False,
    max_records: int = 0,
    max_results_per_record: int = 6,
) -> list[StartupRecord]:
    processed = 0
    for record in records:
        if record.verification_status != "verified":
            continue
        if not record.website and use_tavily:
            record.website = search_company_website_tavily(record)
        if record.founders and all(founder.linkedin_url for founder in record.founders):
            continue
        if max_records and processed >= max_records:
            break
        candidates: list[FounderProfile] = []
        for query in founder_queries(record):
            if use_tavily:
                candidates.extend(search_tavily_linkedin(query, max_results=max_results_per_record))
            if use_exa:
                candidates.extend(search_exa_linkedin(query, max_results=max_results_per_record))
        record.founders.extend(filter_founder_candidates(record, candidates))
        processed += 1
    return records


def search_company_website_tavily(record: StartupRecord) -> str:
    if requests is None:
        return ""
    if not env_keys("TAVILY_API_KEY"):
        return ""
    queries = [
        f'"{record.company_name}" official website',
        f'"{record.company_name}" startup official site',
        f'"{record.company_name}" "{record.funding_round}" "{record.funding_amount}" official website',
    ]
    for query in queries:
        payload = {
            "query": query,
            "search_depth": "basic",
            "include_raw_content": False,
            "include_answer": False,
            "max_results": 8,
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
                url = str(result.get("url") or "")
                if is_probable_company_website(record, url, str(result.get("title") or ""), str(result.get("content") or "")):
                    return url
        except requests.RequestException:
            continue
    return ""


def is_probable_company_website(record: StartupRecord, url: str, title: str, content: str) -> bool:
    parsed = urlparse(url)
    domain = parsed.netloc.lower().removeprefix("www.")
    if not parsed.scheme.startswith("http"):
        return False
    blocked_domains = [
        "techcrunch.com",
        "prnewswire.com",
        "globenewswire.com",
        "businesswire.com",
        "crunchbase.com",
        "alleywatch.com",
        "startuprise.io",
        "medcitynews.com",
        "ecosistemastartup.com",
        "venturebeat.com",
        "siliconangle.com",
        "finsmes.com",
        "techfundingnews.com",
        "linkedin.com",
        "twitter.com",
        "x.com",
        "facebook.com",
        "youtube.com",
    ]
    if any(blocked in domain for blocked in blocked_domains):
        return False
    tokens = company_identity_tokens(record.company_name)
    domain_compact = domain.replace("-", "").replace(".", "")
    company_compact = re.sub(r"[^a-z0-9]+", "", record.company_name.lower())
    if company_compact and company_compact in domain_compact:
        return True
    return bool(tokens) and any(len(token) >= 4 and token in domain_compact for token in tokens)


def founder_queries(record: StartupRecord) -> list[str]:
    amount = record.funding_amount
    round_type = record.funding_round
    pieces = [
        f'"{record.company_name}" "{amount}" founder linkedin',
        f'"{record.company_name}" "{round_type}" founder linkedin',
        f'"{record.company_name}" co-founder site:linkedin.com/in',
        f'"{record.company_name}" founder site:linkedin.com/in',
    ]
    if record.website:
        pieces.insert(0, f'"{record.company_name}" "{domain_from_url(record.website)}" founder linkedin')
    return [query for query in pieces if query.replace('"', "").strip()]


def search_tavily_linkedin(query: str, max_results: int = 6) -> list[FounderProfile]:
    if requests is None:
        return []
    if not env_keys("TAVILY_API_KEY"):
        return []
    payload = {
        "query": query,
        "search_depth": "advanced",
        "include_domains": ["linkedin.com"],
        "include_raw_content": False,
        "include_answer": False,
        "max_results": max_results,
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
        return [candidate_from_search_result(result, "tavily") for result in response.json().get("results", [])]
    except requests.RequestException:
        return []


def search_exa_linkedin(query: str, max_results: int = 6) -> list[FounderProfile]:
    if requests is None:
        return []
    if not env_keys("EXA_API_KEY"):
        return []
    payload = {
        "query": query,
        "numResults": max_results,
        "includeDomains": ["linkedin.com"],
    }
    try:
        response = post_json_with_key_rotation(
            "https://api.exa.ai/search",
            payload,
            env_base="EXA_API_KEY",
            headers_factory=lambda api_key: {"x-api-key": api_key, "Content-Type": "application/json"},
            timeout=30,
        )
        if response is None:
            return []
        if not response.ok:
            return []
        return [candidate_from_search_result(result, "exa") for result in response.json().get("results", [])]
    except requests.RequestException:
        return []


def candidate_from_search_result(result: dict, provider: str) -> FounderProfile:
    title = str(result.get("title") or "")
    url = str(result.get("url") or "")
    content = str(result.get("content") or result.get("text") or "")
    name = extract_person_name_from_linkedin_title(title)
    role = extract_role_from_text(f"{title} {content}")
    return FounderProfile(
        name=name,
        role=role,
        linkedin_url=url,
        evidence=[f"{provider}: {title[:140]}"],
        confidence=50,
        status="needs_review_search_candidate",
    )


def filter_founder_candidates(record: StartupRecord, candidates: list[FounderProfile]) -> list[FounderProfile]:
    accepted: list[FounderProfile] = []
    existing = {(founder.name.lower(), founder.linkedin_url.lower()) for founder in record.founders}
    for candidate in candidates:
        evidence_text = " ".join(candidate.evidence).lower()
        if not candidate.linkedin_url or not is_linkedin_profile(candidate.linkedin_url):
            continue
        if not candidate.name:
            continue
        if not FOUNDER_ROLE_RE.search(candidate.role or evidence_text):
            continue
        if not has_strong_company_role_evidence(record, candidate, evidence_text):
            continue
        key = (candidate.name.lower(), candidate.linkedin_url.lower())
        if key in existing:
            continue
        existing.add(key)
        candidate.evidence.append("search_company_role_match")
        candidate.status = "needs_review_search_candidate"
        candidate.confidence = max(candidate.confidence, 55)
        accepted.append(candidate)
    return accepted


def has_strong_company_role_evidence(record: StartupRecord, candidate: FounderProfile, evidence_text: str) -> bool:
    company = record.company_name.strip().lower()
    if not company:
        return False
    if len(company) <= 3 and candidate.name.lower().startswith(company):
        return False
    escaped = re.escape(company)
    strong_patterns = [
        rf"\b(co[- ]?founder|founder|ceo|chief executive)\b.{{0,80}}\b{escaped}\b",
        rf"\b{escaped}\b.{{0,80}}\b(co[- ]?founder|founder|ceo|chief executive)\b",
        rf"[-|]\s*[^-|]{{0,80}}\b{escaped}\b",
        rf"\bat\s+{escaped}\b",
        rf"\bof\s+{escaped}\b",
    ]
    if any(re.search(pattern, evidence_text, re.I) for pattern in strong_patterns):
        return True
    tokens = [token for token in company_identity_tokens(record.company_name) if len(token) >= 4]
    return bool(tokens) and all(token in evidence_text for token in tokens[:2])


def extract_person_name_from_linkedin_title(title: str) -> str:
    text = re.sub(r"\s*\|\s*LinkedIn.*$", "", title, flags=re.I)
    text = re.split(r"\s+-\s+", text)[0]
    text = re.sub(r"\s+", " ", text).strip()
    if len(text.split()) > 5:
        return ""
    return text


def extract_role_from_text(text: str) -> str:
    match = FOUNDER_ROLE_RE.search(text or "")
    if not match:
        return ""
    role = match.group(1)
    return "Co-founder" if "co" in role.lower() else "Founder" if "founder" in role.lower() else role.upper()


def company_identity_tokens(company: str) -> list[str]:
    return [token for token in re.split(r"[^a-z0-9]+", company.lower()) if len(token) > 2]


def domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    return parsed.netloc.lower().removeprefix("www.")


def identity_signals(record: StartupRecord, founder: FounderProfile) -> list[str]:
    signals: list[str] = []
    if founder.name:
        signals.append("founder_name_present")
    if founder.linkedin_url and is_linkedin_profile(founder.linkedin_url):
        signals.append("public_linkedin_profile")
    if founder.role and FOUNDER_ROLE_RE.search(founder.role):
        signals.append("founder_or_executive_role")
    if record.source_url and record.article_date_verified:
        signals.append("date_verified_funding_source")
    if record.website:
        signals.append("company_website_present")
    return signals


def founder_confidence(signals: list[str]) -> int:
    if len(signals) >= 4:
        return 85
    if len(signals) == 3:
        return 75
    if len(signals) == 2:
        return 65
    return 45


def normalize_person_name(name: str) -> str:
    return re.sub(r"\s+", " ", str(name or "").strip())


def normalize_linkedin_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.scheme:
        text = "https://" + text
        parsed = urlparse(text)
    if "linkedin." not in parsed.netloc.lower():
        return text
    return f"https://{parsed.netloc.lower()}{parsed.path}".rstrip("/")


def is_linkedin_profile(url: str) -> bool:
    parsed = urlparse(url)
    path = parsed.path.lower()
    return "linkedin." in parsed.netloc.lower() and ("/in/" in path or "/pub/" in path)
