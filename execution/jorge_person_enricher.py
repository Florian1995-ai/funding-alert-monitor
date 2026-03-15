#!/usr/bin/env python3
"""
Jorge Person Enricher - Deep research on decision makers

Finds comprehensive social profiles and personal signals for each person:
- LinkedIn (existing)
- Instagram (NEW)
- Facebook (NEW)
- Email (IMPROVED - multi-source)
- Company Website + Domain (NEW)
- Personal Signal for PS line (NEW)

This script does NOT modify existing files - it's an additive enhancement.
"""

import os
import re
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent


# ─── Name Cleaning Utilities ───────────────────────────────────────────────────

def clean_linkedin_name(raw_name: str) -> dict:
    """
    Clean a name extracted from a LinkedIn URL slug.

    Handles:
    1. LinkedIn ID suffixes (e.g., "Piotr Dabkowski 50222Bba" -> "Piotr Dabkowski")
    2. Handle-style names (e.g., "Siddharthsrinivasan" -> needs Tavily resolution)

    Returns dict with cleaned_name, needs_resolution flag, and original.
    """
    if not raw_name or raw_name.lower() in ["there", "unknown"]:
        return {"cleaned_name": raw_name, "needs_resolution": False, "original": raw_name}

    # Step 1: Strip LinkedIn ID suffixes
    # These are alphanumeric sequences at the end that contain digits
    # e.g. "Piotr Dabkowski 50222Bba" -> drop "50222Bba"
    words = raw_name.split()
    cleaned_words = []
    for i, word in enumerate(words):
        if i < len(words) - 1:
            cleaned_words.append(word)
        else:
            # Last word: drop if it contains any digit
            if re.search(r'\d', word):
                continue
            else:
                cleaned_words.append(word)

    cleaned_name = " ".join(cleaned_words).strip()
    if not cleaned_name:
        cleaned_name = raw_name

    # Step 2: Detect handle-style names (single word, no spaces)
    # Real names almost always have first + last
    needs_resolution = False
    name_words = cleaned_name.split()

    if len(name_words) == 1:
        needs_resolution = True

    return {
        "cleaned_name": cleaned_name,
        "needs_resolution": needs_resolution,
        "original": raw_name,
    }


def extract_name_from_linkedin_title(title: str, company: str) -> str:
    """
    Extract a proper name from a LinkedIn profile page title.

    LinkedIn titles follow: "First Last - Role at Company | LinkedIn"
    or: "First Last | LinkedIn"

    Returns the name if found, empty string otherwise.
    """
    if not title:
        return ""

    # Pattern: "Name - Something" or "Name | Something"
    match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*[-|–]', title)
    if match:
        candidate = match.group(1).strip()
        if len(candidate.split()) >= 2 and company.lower() not in candidate.lower():
            return candidate

    # Fallback: title is just "First Last" with no separator
    match = re.match(r'^([A-Z][a-z]+\s+[A-Z][a-z]+)$', title.strip())
    if match:
        return match.group(1)

    return ""


def _extract_name_from_text(text: str, handle: str, company: str) -> str:
    """Extract a proper full name from text, using the handle as a hint."""
    if not text:
        return ""

    name_pattern = r'([A-Z][a-z]{1,15})\s+([A-Z][a-z]{1,20})'
    matches = re.findall(name_pattern, text)

    skip_words = {"the", "this", "linkedin", "about", "series", "round",
                  "read", "more", "view", "click", "sign", "join", "from"}

    # First pass: look for names matching the handle hint
    handle_lower = handle.lower().replace(" ", "")
    for first, last in matches:
        if first.lower() in skip_words or company.lower() == f"{first} {last}".lower():
            continue
        first_lower = first.lower()
        if handle_lower.startswith(first_lower) or first_lower.startswith(handle_lower[:4]):
            return f"{first} {last}"

    # Second pass: return first valid-looking name
    for first, last in matches:
        if first.lower() in skip_words or company.lower() == f"{first} {last}".lower():
            continue
        return f"{first} {last}"

    return ""


def resolve_name_via_tavily(handle: str, company: str, linkedin_url: str = "") -> str:
    """
    Resolve a LinkedIn handle/slug to a full name using Tavily search.

    Costs ~$0.005 per call (basic search depth).
    """
    api_key = get_tavily_api_key()
    if not api_key:
        return handle

    queries = []
    if linkedin_url:
        queries.append(f'{linkedin_url} name')
    queries.append(f'"{handle}" {company} LinkedIn')
    queries.append(f'{handle} {company} CEO OR CTO OR founder')

    for query in queries:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "basic",
                    "max_results": 5,
                    "include_answer": True,
                },
                timeout=30
            )

            if response.ok:
                data = response.json()

                # Check Tavily's answer field
                answer = data.get("answer", "")
                if answer:
                    name_match = _extract_name_from_text(answer, handle, company)
                    if name_match:
                        print(f"         [RESOLVED] {handle} -> {name_match} (via Tavily answer)")
                        return name_match

                # Check search result titles
                # LinkedIn titles: "Siddharth Srinivasan - CTO at ElevenLabs | LinkedIn"
                for result in data.get("results", []):
                    title = result.get("title", "")
                    content = result.get("content", "")

                    title_name = re.match(
                        r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*[-|–]',
                        title
                    )
                    if title_name:
                        candidate = title_name.group(1).strip()
                        if len(candidate.split()) >= 2 and company.lower() not in candidate.lower():
                            print(f"         [RESOLVED] {handle} -> {candidate} (via Tavily title)")
                            return candidate

                    name_match = _extract_name_from_text(content, handle, company)
                    if name_match:
                        print(f"         [RESOLVED] {handle} -> {name_match} (via Tavily content)")
                        return name_match

            time.sleep(0.3)

        except Exception as e:
            print(f"      [WARN] Tavily name resolution failed: {e}")

    # Fallback: Try Perplexity to resolve the handle
    api_key = get_perplexity_api_key()
    if api_key:
        try:
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "sonar",
                    "messages": [{
                        "role": "user",
                        "content": f"Who is {handle} at {company}? Just return their full name (first and last name only)."
                    }],
                    "max_tokens": 50,
                },
                timeout=30
            )

            if response.ok:
                content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
                # Clean markdown artifacts and citations
                content = re.sub(r'\*\*', '', content)  # Remove bold markers
                content = re.sub(r'\[[\d,\s]+\]', '', content)  # Remove [1][2] citations
                content = content.strip('"\'.')
                # Extract the name (first sentence usually has it)
                name_match = re.match(r'^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', content)
                if name_match:
                    resolved = name_match.group(1).strip()
                    if 2 <= len(resolved.split()) <= 4:
                        print(f"         [RESOLVED] {handle} -> {resolved} (via Perplexity)")
                        return resolved
        except Exception as e:
            print(f"      [WARN] Perplexity name resolution failed: {e}")

    print(f"      [WARN] Could not resolve handle '{handle}' - keeping as-is")
    return handle


# ─── API Key Helpers ───────────────────────────────────────────────────────────

def get_exa_api_key() -> str:
    """Get a working Exa API key with rotation."""
    keys = [
        os.environ.get("EXA_API_KEY"),
        os.environ.get("EXA_API_KEY_2"),
        os.environ.get("EXA_API_KEY_3"),
        os.environ.get("EXA_API_KEY_4"),
    ]
    for key in keys:
        if key:
            return key
    return ""


def get_perplexity_api_key() -> str:
    """Get Perplexity API key."""
    return os.environ.get("PERPLEXITY_API_KEY", "")


def get_apify_api_token() -> str:
    """Get Apify API token with rotation."""
    keys = [
        os.environ.get("APIFY_API_TOKEN"),
        os.environ.get("APIFY_API_TOKEN_2"),
        os.environ.get("APIFY_API_TOKEN_3"),
    ]
    for key in keys:
        if key:
            return key
    return ""


def search_instagram_exa(name: str, company: str) -> str:
    """Find Instagram profile for a person using Exa."""
    api_key = get_exa_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "query": f"{name} {company} Instagram profile",
                "type": "neural",
                "numResults": 5,
                "includeDomains": ["instagram.com"],
            },
            timeout=30
        )

        if response.ok:
            for r in response.json().get("results", []):
                url = r.get("url", "")
                # Validate it's a profile URL, not a post
                if "instagram.com/" in url and "/p/" not in url and "/reel/" not in url:
                    return url
    except Exception as e:
        print(f"      [WARN] Instagram search failed: {e}")

    return ""


def search_facebook_exa(name: str, company: str) -> str:
    """Find Facebook profile for a person using Exa."""
    api_key = get_exa_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "query": f"{name} {company} Facebook profile",
                "type": "neural",
                "numResults": 5,
                "includeDomains": ["facebook.com"],
            },
            timeout=30
        )

        if response.ok:
            for r in response.json().get("results", []):
                url = r.get("url", "")
                # Validate it's a profile URL
                if "facebook.com/" in url and "/posts/" not in url and "/photos/" not in url:
                    return url
    except Exception as e:
        print(f"      [WARN] Facebook search failed: {e}")

    return ""


def search_twitter_exa(name: str, company: str) -> str:
    """Find Twitter/X profile for a person using Exa."""
    api_key = get_exa_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "query": f"{name} {company} Twitter",
                "type": "neural",
                "numResults": 5,
                "includeDomains": ["twitter.com", "x.com"],
            },
            timeout=30
        )

        if response.ok:
            for r in response.json().get("results", []):
                url = r.get("url", "")
                if "twitter.com/" in url or "x.com/" in url:
                    # Exclude status URLs (tweets)
                    if "/status/" not in url:
                        return url
    except Exception as e:
        print(f"      [WARN] Twitter search failed: {e}")

    return ""


def find_company_website_exa(company: str) -> str:
    """Find company website using Exa neural search."""
    api_key = get_exa_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": api_key,
                "Content-Type": "application/json",
            },
            json={
                "query": f"{company} official website homepage",
                "type": "neural",
                "numResults": 5,
            },
            timeout=30
        )

        if response.ok:
            for r in response.json().get("results", []):
                url = r.get("url", "")
                # Skip social media and news sites
                excluded = ["linkedin.com", "twitter.com", "facebook.com", "crunchbase.com",
                           "techcrunch.com", "bloomberg.com", "reuters.com", "wikipedia.org"]
                if not any(ex in url.lower() for ex in excluded):
                    return url
    except Exception as e:
        print(f"      [WARN] Company website search failed: {e}")

    return ""


def research_company_feature_focus(company: str, company_website: str = "", about_summary: str = "") -> str:
    """
    Research the company to generate a dynamic feature focus for emails.

    Returns something like: "build out your AI inference pipeline" or
    "scale your operational intelligence platform"
    """
    api_key = get_perplexity_api_key()
    if not api_key:
        return "accelerate your roadmap"

    # Use about summary if available, otherwise research
    context = about_summary if about_summary else f"Company website: {company_website}" if company_website else ""

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [{
                    "role": "user",
                    "content": f"""Research {company} and find what they plan to use their recent funding for.

{context}

Check their press release, funding announcement, or website to find:
1. What they said they'll use the funds for (e.g., "expand engineering team", "launch enterprise product")
2. If no press release found, identify their main product/feature that seems most valuable

Return a SHORT phrase (5-10 words max) describing what a dev team would help them with. Be SPECIFIC to this company — never say "roadmap" or generic terms.

Examples of good responses:
- "build out your AI inference pipeline"
- "scale your voice synthesis platform"
- "expand your fintech payment integrations"
- "launch your enterprise observability product"
- "develop your autonomous agent framework"

Return ONLY the phrase, nothing else. Start with a verb like "build", "scale", "expand", "develop", "launch"."""
                }],
                "max_tokens": 50,
            },
            timeout=30
        )

        if response.ok:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # Clean markdown artifacts
            content = re.sub(r'\*\*', '', content)
            content = re.sub(r'\[[\d,\s]+\]', '', content)
            content = content.strip('"\'').strip()
            # Take first line only
            content = content.split('\n')[0].strip()
            # Validate it's reasonable length and not generic
            if 3 < len(content) < 80 and "roadmap" not in content.lower():
                if content[0].islower():
                    return content
                else:
                    return content[0].lower() + content[1:]

    except Exception as e:
        print(f"      [WARN] Feature focus research failed: {e}")

    return "accelerate your roadmap"


def search_hiring_signals(company: str) -> list:
    """
    Dedicated search for company hiring signals.

    Searches:
    1. LinkedIn job postings
    2. Lever/Greenhouse/Ashby careers pages
    3. "We're hiring" announcements

    Returns list of hiring signals with role, level, source, and date.
    """
    api_key = get_exa_api_key()
    if not api_key:
        return []

    hiring_signals = []
    seen_roles = set()

    # Define role keywords and their seniority levels
    role_levels = {
        "founding": "Founding/Early",
        "senior": "Senior",
        "staff": "Staff",
        "principal": "Principal",
        "lead": "Lead",
        "head of": "Head/Director",
        "director": "Head/Director",
        "vp": "VP/Executive",
        "chief": "Executive",
        "junior": "Junior",
        "intern": "Intern",
    }

    queries = [
        f'"{company}" hiring OR careers OR "we\'re hiring" OR "join our team"',
        f'site:linkedin.com/jobs "{company}"',
        f'site:lever.co "{company}" OR site:greenhouse.io "{company}" OR site:ashbyhq.com "{company}"',
    ]

    for query in queries:
        try:
            response = requests.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "type": "keyword" if "site:" in query else "neural",
                    "numResults": 10,
                    "contents": {"text": {"maxCharacters": 1500}},
                },
                timeout=30
            )

            if response.ok:
                for r in response.json().get("results", []):
                    title = r.get("title", "")
                    text = r.get("text", "") or ""
                    url = r.get("url", "")
                    combined = (title + " " + text).lower()

                    # Skip if company name not mentioned
                    if company.lower() not in combined:
                        continue

                    # Extract role patterns
                    role_patterns = [
                        r'hiring\s+(?:a\s+)?([a-z\s]+(?:engineer|developer|designer|manager|pm|sdr|bdr|lead|head|director|vp))',
                        r'(?:senior|staff|principal|founding|lead)\s+([a-z\s]+(?:engineer|developer|designer))',
                        r'([a-z\s]*(?:product manager|engineering manager|chief of staff|head of [a-z]+))',
                        r'open\s+(?:role|position)[:\s]+([a-z\s]+)',
                    ]

                    for pattern in role_patterns:
                        matches = re.findall(pattern, combined)
                        for match in matches:
                            role = match.strip().title()
                            if len(role) < 3 or role in seen_roles:
                                continue

                            # Determine level
                            level = "Mid-level"
                            for keyword, lvl in role_levels.items():
                                if keyword in match.lower():
                                    level = lvl
                                    break

                            # Extract date hint from text
                            date_hint = "Recent"
                            date_patterns = [
                                r'(january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}?,?\s*2026',
                                r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}?,?\s*2026',
                                r'(\d{1,2})\s+(days?|weeks?|months?)\s+ago',
                            ]
                            for dp in date_patterns:
                                dm = re.search(dp, combined)
                                if dm:
                                    date_hint = dm.group(0).title()
                                    break

                            seen_roles.add(role)
                            hiring_signals.append({
                                "role": role,
                                "level": level,
                                "source": url[:80] if url else "Search result",
                                "date_hint": date_hint,
                            })

            time.sleep(0.3)

        except Exception as e:
            print(f"      [WARN] Hiring signals search failed: {e}")

    return hiring_signals[:10]  # Limit to top 10


def extract_domain_from_url(url: str) -> str:
    """Extract domain from a URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except Exception:
        return ""


def generate_email_patterns(first_name: str, last_name: str, domain: str) -> list:
    """Generate common email patterns for a person."""
    if not domain or not first_name:
        return []

    first = first_name.lower().strip()
    last = last_name.lower().strip() if last_name else ""

    patterns = [
        f"{first}@{domain}",
        f"{first}.{last}@{domain}" if last else None,
        f"{first[0]}{last}@{domain}" if last else None,
        f"{first}{last[0]}@{domain}" if last else None,
        f"{first}_{last}@{domain}" if last else None,
        f"{first}-{last}@{domain}" if last else None,
        f"{last}@{domain}" if last else None,
    ]

    return [p for p in patterns if p]


def search_email_apify_google(name: str, company: str) -> str:
    """Search for email using Apify Google Search scraper."""
    api_token = get_apify_api_token()
    if not api_token:
        return ""

    try:
        from apify_client import ApifyClient
        client = ApifyClient(api_token)

        query = f'"{name}" "{company}" email "@"'

        run_input = {
            "queries": query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 10,
            "mobileResults": False,
            "languageCode": "en",
            "countryCode": "us",
        }

        run = client.actor("apify/google-search-scraper").call(run_input=run_input, timeout_secs=60)

        if run:
            for item in client.dataset(run["defaultDatasetId"]).iterate_items():
                organic = item.get("organicResults", [])
                for result in organic:
                    text = (result.get("title", "") + " " + result.get("description", "")).lower()
                    # Look for email patterns in search results
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                    if email_match:
                        email = email_match.group(0)
                        # Filter out generic emails
                        if not any(x in email.lower() for x in ["example", "test", "sample", "domain", "email.com", "mail.com"]):
                            return email
    except ImportError:
        print("      [WARN] apify_client not installed")
    except Exception as e:
        print(f"      [WARN] Apify Google search failed: {e}")

    return ""


def find_email_perplexity_improved(name: str, company: str, company_domain: str = "") -> str:
    """
    Try to find email using Perplexity with improved prompt.
    Uses company domain for more accurate results.
    """
    api_key = get_perplexity_api_key()
    if not api_key:
        return ""

    domain_hint = f"The company's domain is {company_domain}." if company_domain else ""

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [{
                    "role": "user",
                    "content": f"""Find the work email address of {name}, who works at {company}. {domain_hint}

Search for:
1. Their LinkedIn profile (often shows email or "Contact info")
2. Company website team/about page
3. Press releases or interviews mentioning them
4. Conference speaker bios
5. GitHub profiles (often have email)

Return ONLY the email address if found (like name@company.com). If not found, return "NOT_FOUND"."""
                }],
                "max_tokens": 150,
            },
            timeout=45
        )

        if response.ok:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

            if "NOT_FOUND" in content.upper():
                return ""

            email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', content)
            if email_match:
                email = email_match.group(0)
                # Filter out example/test emails
                if not any(x in email.lower() for x in ["example", "test", "sample", "domain", "email.com"]):
                    return email
    except Exception as e:
        print(f"      [WARN] Perplexity email lookup failed: {e}")

    return ""


def get_tavily_api_key() -> str:
    """Get a working Tavily API key with rotation."""
    keys = [
        os.environ.get("TAVILY_API_KEY"),
        os.environ.get("TAVILY_API_KEY_2"),
        os.environ.get("TAVILY_API_KEY_3"),
        os.environ.get("TAVILY_API_KEY_4"),
    ]
    for key in keys:
        if key:
            return key
    return ""


def search_email_tavily(name: str, company: str) -> str:
    """Search for email using Tavily deep search."""
    api_key = get_tavily_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": f'"{name}" "{company}" email contact',
                "search_depth": "advanced",
                "max_results": 10,
                "include_answer": True,
            },
            timeout=30
        )

        if response.ok:
            data = response.json()
            # Check answer field first
            answer = data.get("answer", "")
            if answer:
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', answer)
                if email_match:
                    email = email_match.group(0)
                    if not any(x in email.lower() for x in ["example", "test", "sample"]):
                        return email

            # Check search results
            for result in data.get("results", []):
                text = result.get("content", "") + " " + result.get("title", "")
                email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                if email_match:
                    email = email_match.group(0)
                    if not any(x in email.lower() for x in ["example", "test", "sample"]):
                        return email
    except Exception as e:
        print(f"      [WARN] Tavily email search failed: {e}")

    return ""


def search_email_exa(name: str, company: str, domain: str = "") -> str:
    """Search for email using Exa neural search."""
    api_key = get_exa_api_key()
    if not api_key:
        return ""

    # Try multiple query variations
    queries = [
        f'"{name}" "{company}" email contact',
        f'"{name}" {company} "@{domain}"' if domain else None,
        f'{name} founder {company} email',
    ]

    for query in queries:
        if not query:
            continue

        try:
            response = requests.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "type": "neural",
                    "numResults": 10,
                    "contents": {"text": True},
                },
                timeout=30
            )

            if response.ok:
                for r in response.json().get("results", []):
                    text = r.get("text", "") + " " + r.get("title", "")
                    email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
                    if email_match:
                        email = email_match.group(0)
                        # Validate email looks legitimate
                        if not any(x in email.lower() for x in ["example", "test", "sample", "email.com"]):
                            # Prefer emails from the company domain
                            if domain and domain in email:
                                return email
                            # Otherwise return first valid email
                            return email

            time.sleep(0.3)

        except Exception as e:
            print(f"      [WARN] Exa email search failed: {e}")

    return ""


def validate_email_domain(email: str, expected_domain: str) -> bool:
    """Check if email matches expected company domain."""
    if not email or not expected_domain:
        return False
    email_domain = email.split("@")[-1].lower()
    expected = expected_domain.lower()
    # Direct match or subdomain match
    return email_domain == expected or email_domain.endswith("." + expected)


def find_email_multi_source(name: str, company: str, company_website: str = "") -> dict:
    """
    Try multiple sources to find email address.
    Prioritizes emails matching the company domain.
    Returns dict with email and source used.
    """
    # Extract domain from website if available
    domain = extract_domain_from_url(company_website) if company_website else ""

    # Parse name for patterns
    name_parts = name.split()
    first_name = name_parts[0] if name_parts else ""
    last_name = name_parts[-1] if len(name_parts) > 1 else ""

    result = {"email": "", "source": "", "patterns": []}

    # Collect all found emails with their sources
    found_emails = []

    # Method 1: Perplexity (improved prompt with domain hint)
    print("         [1/4] Perplexity deep search...")
    email = find_email_perplexity_improved(name, company, domain)
    if email:
        found_emails.append({"email": email, "source": "perplexity"})

    time.sleep(0.3)

    # Method 2: Tavily deep search
    print("         [2/4] Tavily search...")
    email = search_email_tavily(name, company)
    if email and email not in [e["email"] for e in found_emails]:
        found_emails.append({"email": email, "source": "tavily"})

    time.sleep(0.3)

    # Method 3: Exa neural search
    print("         [3/4] Exa neural search...")
    email = search_email_exa(name, company, domain)
    if email and email not in [e["email"] for e in found_emails]:
        found_emails.append({"email": email, "source": "exa"})

    time.sleep(0.3)

    # Method 4: Generate email patterns
    patterns = []
    if domain:
        print("         [4/4] Generating email patterns...")
        patterns = generate_email_patterns(first_name, last_name, domain)
        result["patterns"] = patterns[:3]

    # Select best email: prioritize domain matches
    if found_emails and domain:
        # First check for exact domain matches
        for item in found_emails:
            if validate_email_domain(item["email"], domain):
                result["email"] = item["email"]
                result["source"] = item["source"] + "_domain_match"
                print(f"         [OK] Domain-validated email: {item['email']}")
                return result

        # If no domain match, check if first name appears in email
        first_lower = first_name.lower() if first_name else ""
        for item in found_emails:
            email_local = item["email"].split("@")[0].lower()
            if first_lower and first_lower in email_local:
                result["email"] = item["email"]
                result["source"] = item["source"] + "_name_match"
                print(f"         [!] Name-matched email (unverified domain): {item['email']}")
                return result

    # If still no good match, use pattern guess if domain available
    if not result["email"] and patterns:
        result["email"] = patterns[0]
        result["source"] = "pattern_guess"
        print(f"         [!] Using pattern guess: {patterns[0]}")
        return result

    # Last resort: return first found email if any
    if found_emails:
        result["email"] = found_emails[0]["email"]
        result["source"] = found_emails[0]["source"] + "_unverified"
        print(f"         [!] Unverified email: {found_emails[0]['email']}")
        return result

    return result


def get_personal_signal_perplexity(name: str, company: str, role: str) -> dict:
    """
    Get personal signal for PS line personalization using Perplexity.

    Returns:
    {
        "source": "LinkedIn post, Jan 2026",
        "summary": "Excited about democratizing AI inference",
        "hook_for_ps": "Your post about 'making AI inference effortless' resonates..."
    }
    """
    api_key = get_perplexity_api_key()
    if not api_key:
        return {"source": "", "summary": "", "hook_for_ps": ""}

    try:
        prompt = f"""Research {name}, {role} at {company}. Find ONE recent personal signal I can reference in a cold email PS line.

Look for:
1. Recent LinkedIn post (last 30 days) - topic and key insight
2. Recent podcast appearance - what they discussed
3. Twitter/X activity - any strong opinions or announcements
4. Blog post or article they wrote
5. Conference talk or interview

Return in this exact format:
SOURCE: [where you found it, e.g., "LinkedIn post, Jan 22, 2026"]
SUMMARY: [1 sentence summary of what they said/did]
PS_HOOK: [Write a personalized PS line that references this authentically, max 100 chars]

If you can't find anything specific, return:
SOURCE: none
SUMMARY: none
PS_HOOK: none"""

        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 500,
            },
            timeout=45
        )

        if response.ok:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse the response
            source = ""
            summary = ""
            hook = ""

            for line in content.split("\n"):
                line = line.strip()
                if line.upper().startswith("SOURCE:"):
                    source = line.split(":", 1)[1].strip()
                elif line.upper().startswith("SUMMARY:"):
                    summary = line.split(":", 1)[1].strip()
                elif line.upper().startswith("PS_HOOK:") or line.upper().startswith("PS HOOK:"):
                    hook = line.split(":", 1)[1].strip()

            # Clean up "none" responses
            if source.lower() == "none" or not source:
                source = ""
            if summary.lower() == "none" or not summary:
                summary = ""
            if hook.lower() == "none" or not hook:
                hook = ""

            return {
                "source": source,
                "summary": summary,
                "hook_for_ps": hook
            }

    except Exception as e:
        print(f"      [WARN] Personal signal lookup failed: {e}")

    return {"source": "", "summary": "", "hook_for_ps": ""}


def get_location_perplexity(name: str, company: str) -> str:
    """Try to find person's location using Perplexity."""
    api_key = get_perplexity_api_key()
    if not api_key:
        return ""

    try:
        response = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "sonar",
                "messages": [{
                    "role": "user",
                    "content": f"What city is {name}, {company} based in? Just return the city name (e.g., 'New York City' or 'San Francisco'). If you can't find it, return 'Unknown'."
                }],
                "max_tokens": 50,
            },
            timeout=30
        )

        if response.ok:
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content", "").strip()
            # Clean markdown artifacts and citations from Sonar
            content = re.sub(r'\*\*', '', content)  # Remove bold markers
            content = re.sub(r'\[[\d,\s]+\]', '', content)  # Remove [1][2] citations
            content = content.strip()
            # Clean up response
            if content and content.lower() not in ["unknown", "not found", "i don't know", "i cannot"]:
                # Remove common prefixes
                for prefix in ["Based in ", "Located in ", "They are in ", "The location is "]:
                    if content.startswith(prefix):
                        content = content[len(prefix):]
                # Take only the first line/sentence (city name)
                content = content.split('\n')[0].split('.')[0].strip()
                if content and len(content) < 50:
                    return content.strip().rstrip(".")
    except Exception as e:
        print(f"      [WARN] Location lookup failed: {e}")

    return ""


def enrich_person(name: str, company: str, role: str, existing_data: dict = None, company_website: str = "") -> dict:
    """
    Fully enrich a person with all social channels and personal signal.

    Args:
        name: Person's full name
        company: Company name
        role: Person's role (CEO, CTO, etc.)
        existing_data: Any existing data (LinkedIn URL, etc.)
        company_website: Company website URL (for email pattern generation)

    Returns:
        Enriched person dict with all channels and personal signal
    """
    if existing_data is None:
        existing_data = {}

    # Safety net: clean name even if it slipped through uncleaned from orchestrator
    name_info = clean_linkedin_name(name)
    if name_info["needs_resolution"]:
        print(f"      [NAME] Name '{name}' looks like a handle - attempting resolution...")
        name = resolve_name_via_tavily(
            name, company, existing_data.get("linkedin_url", "")
        )
    elif name_info["cleaned_name"] != name:
        print(f"      [NAME] Cleaned: '{name}' -> '{name_info['cleaned_name']}'")
        name = name_info["cleaned_name"]

    result = {
        "name": name,
        "role": role,
        "company": company,
        "linkedin_url": existing_data.get("linkedin_url", ""),
        "twitter_url": existing_data.get("twitter_url", ""),
        "instagram_url": existing_data.get("instagram_url", ""),
        "facebook_url": existing_data.get("facebook_url", ""),
        "email": existing_data.get("email", ""),
        "email_source": "",
        "email_patterns": [],
        "location": existing_data.get("location", ""),
        "interests": existing_data.get("interests", []),
        "personal_signal": {
            "source": "",
            "summary": "",
            "hook_for_ps": ""
        }
    }

    print(f"      Enriching {name} ({role})...")

    # Find Twitter if not already present
    if not result["twitter_url"]:
        print(f"         Searching Twitter...")
        result["twitter_url"] = search_twitter_exa(name, company)
        if result["twitter_url"]:
            print(f"         [OK] Twitter: {result['twitter_url'][:50]}...")
        time.sleep(0.3)

    # Find Instagram
    if not result["instagram_url"]:
        print(f"         Searching Instagram...")
        result["instagram_url"] = search_instagram_exa(name, company)
        if result["instagram_url"]:
            print(f"         [OK] Instagram: {result['instagram_url'][:50]}...")
        time.sleep(0.3)

    # Find Facebook
    if not result["facebook_url"]:
        print(f"         Searching Facebook...")
        result["facebook_url"] = search_facebook_exa(name, company)
        if result["facebook_url"]:
            print(f"         [OK] Facebook: {result['facebook_url'][:50]}...")
        time.sleep(0.3)

    # Find email using multi-source approach
    if not result["email"]:
        print(f"         Searching email (multi-source)...")
        email_result = find_email_multi_source(name, company, company_website)
        if email_result["email"]:
            result["email"] = email_result["email"]
            result["email_source"] = email_result["source"]
            result["email_patterns"] = email_result.get("patterns", [])
            source_label = email_result["source"]
            if source_label == "pattern_guess":
                print(f"         [!] Email (guessed pattern): {result['email']}")
            else:
                print(f"         [OK] Email ({source_label}): {result['email']}")
        else:
            print(f"         [!] Email not found via any source")

    # Find location if not already present
    if not result["location"]:
        print(f"         Searching location...")
        result["location"] = get_location_perplexity(name, company)
        if result["location"]:
            print(f"         [OK] Location: {result['location']}")
        else:
            print(f"         [!] Location not found")
        time.sleep(0.3)

    # Get personal signal for PS line
    print(f"         Researching personal signal for PS line...")
    result["personal_signal"] = get_personal_signal_perplexity(name, company, role)
    if result["personal_signal"]["hook_for_ps"]:
        print(f"         [OK] Personal signal found: {result['personal_signal']['source']}")
    else:
        print(f"         [!] No personal signal found - will use generic PS")

    return result


def enrich_all_decision_makers(company: str, decision_makers: list, company_website: str = "") -> list:
    """
    Enrich all decision makers for a company.

    Args:
        company: Company name
        decision_makers: List of dicts with name, role, linkedin_url, etc.
        company_website: Company website URL (for email pattern generation)

    Returns:
        List of fully enriched person dicts
    """
    enriched = []

    # If no website provided, try to find it
    if not company_website:
        print(f"      Looking up company website...")
        company_website = find_company_website_exa(company)
        if company_website:
            print(f"      [OK] Company website: {company_website}")
        else:
            print(f"      [!] Company website not found")

    for person in decision_makers:
        name = person.get("name", "")
        role = person.get("role", "Executive")

        if not name or name.lower() == "there":
            continue

        enriched_person = enrich_person(
            name=name,
            company=company,
            role=role,
            existing_data=person,
            company_website=company_website
        )
        enriched.append(enriched_person)

        # Rate limiting between people
        time.sleep(0.5)

    return enriched


if __name__ == "__main__":
    # Test the enricher
    print("Testing person enricher...")

    test_person = enrich_person(
        name="Simon Mo",
        company="Inferact",
        role="CEO"
    )

    print("\n" + "="*60)
    print("ENRICHMENT RESULT:")
    print("="*60)
    print(json.dumps(test_person, indent=2))
