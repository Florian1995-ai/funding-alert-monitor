#!/usr/bin/env python3
"""
Jorge MVP Orchestrator

Main workflow that ties all components together:
1. Find recently funded US companies (Tavily)
2. Find 3 decision makers: CEO, CTO, HR/COO (Exa)
3. Enrich each person with all social channels + personal signals
4. Generate SEPARATE research report (markdown)
5. Generate SEPARATE email drafts with cross-refs + personalized PS
6. Create Gmail drafts

Usage:
    # Demo run - 1 company, drafts to your email
    python execution/jorge_mvp_orchestrator.py --region us --limit 1 --send --target florian

    # Dry run - no drafts
    python execution/jorge_mvp_orchestrator.py --region us --limit 1 --dry-run

    # Production - drafts to Jorge's Gmail
    python execution/jorge_mvp_orchestrator.py --region us --limit 3 --send --target jorge
"""

import os
import sys
import json
import argparse
import base64
import time
import re
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from dotenv import load_dotenv

load_dotenv()

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "execution"))

# Import our new modules
from jorge_person_enricher import (
    enrich_all_decision_makers, search_hiring_signals, research_company_feature_focus,
    clean_linkedin_name, resolve_name_via_tavily, extract_name_from_linkedin_title
)
from jorge_research_report import generate_research_report
from jorge_email_generator import generate_all_emails

# Paths
TMP_DIR = PROJECT_ROOT / ".tmp"
SEEN_FILE = TMP_DIR / "seen_jorge_mvp.json"

# Gmail token paths
GMAIL_TOKENS = {
    "florian": PROJECT_ROOT / "token_gmail.json",
    "jorge": PROJECT_ROOT / "token_jorge_gmail.json",
}

# Target roles for decision makers
TARGET_ROLES = [
    "CEO", "CTO", "COO", "CFO",
    "Founder", "Co-founder", "Co-Founder",
    "VP Engineering", "VP of Engineering", "Head of Engineering",
    "Head of HR", "VP People", "Head of People", "People Operations",
    "Chief of Staff",
]

# Region configs
REGIONS = {
    "us": {
        "queries_suffix": "startup",
        "domains": ["techcrunch.com", "venturebeat.com"],
        "language": "en",
        "countries": ["united states", "usa", "san francisco", "new york", "boston", "austin", "seattle", "los angeles"],
    },
    "eu": {
        "queries_suffix": "Europe European startup",
        "domains": ["sifted.eu", "tech.eu", "eu-startups.com"],
        "language": "en",
        "countries": ["germany", "france", "uk", "netherlands", "sweden", "ireland", "portugal", "italy"],
    },
    "spain": {
        "queries_suffix": "Spain Spanish startup",
        "domains": ["elpais.com", "expansion.com", "cincodias.elpais.com"],
        "language": "es",
        "countries": ["spain", "españa", "madrid", "barcelona"],
    },
}


def load_seen() -> dict:
    """Load previously seen companies."""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, 'r') as f:
                data = json.load(f)
                cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
                data["companies"] = {
                    k: v for k, v in data.get("companies", {}).items()
                    if v.get("seen_at", "") > cutoff
                }
                return data
        except Exception:
            pass
    return {"companies": {}, "last_run": None}


def save_seen(data: dict):
    """Save seen companies."""
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(SEEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_tavily_api_key() -> str:
    """Get a working Tavily API key."""
    keys = [
        os.environ.get("TAVILY_API_KEY"),
        os.environ.get("TAVILY_API_KEY_2"),
        os.environ.get("TAVILY_API_KEY_3"),
    ]
    for key in keys:
        if key:
            return key
    return ""


def get_exa_api_key() -> str:
    """Get a working Exa API key."""
    keys = [
        os.environ.get("EXA_API_KEY"),
        os.environ.get("EXA_API_KEY_2"),
        os.environ.get("EXA_API_KEY_3"),
    ]
    for key in keys:
        if key:
            return key
    return ""


def search_funding_tavily(region: str = "us", limit: int = 10, days_back: int = 7) -> list:
    """Search for recent funding announcements using Tavily."""
    api_key = get_tavily_api_key()
    if not api_key:
        print("[ERROR] No TAVILY_API_KEY found")
        return []

    region_config = REGIONS.get(region, REGIONS["us"])
    suffix = region_config["queries_suffix"]

    queries = [
        f'"raises" "million" funding {suffix}',
        f'"secures" "funding" startup {suffix}',
        f'"Series A" OR "Series B" OR "seed round" {suffix}',
    ]

    include_domains = [
        "techcrunch.com",
        "businesswire.com",
        "prnewswire.com",
        "crunchbase.com",
        "globenewswire.com",
    ] + region_config.get("domains", [])

    all_results = []

    print(f"[INFO] Searching for {region.upper()} funding announcements (last {days_back} days)...")

    for query in queries:
        try:
            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": limit,
                    "include_domains": include_domains,
                    "days": days_back,
                },
                timeout=30
            )

            if response.ok:
                results = response.json().get("results", [])
                all_results.extend(results)
            else:
                print(f"[WARN] Tavily returned {response.status_code}")

        except Exception as e:
            print(f"[WARN] Tavily search failed: {e}")

        time.sleep(0.3)

    # Deduplicate by URL
    seen_urls = set()
    unique_results = []
    for r in all_results:
        url = r.get("url", "")
        if url not in seen_urls:
            seen_urls.add(url)
            unique_results.append(r)

    print(f"[INFO] Found {len(unique_results)} unique articles")
    return unique_results


def extract_company_info(result: dict) -> dict:
    """Extract company info from a funding article."""
    title = result.get("title", "")
    content = result.get("content", "")
    url = result.get("url", "")
    text = title + " " + content

    # Extract company name
    company = "Unknown"
    patterns = [
        r'^([A-Z][A-Za-z0-9]+(?:\.[A-Za-z]+)?)\s+[Rr]aises',
        r'^([A-Z][A-Za-z0-9]+(?:\.[A-Za-z]+)?)\s+[Ss]ecures',
        r'^([A-Z][A-Za-z0-9]+(?:\.[A-Za-z]+)?)\s+[Cc]loses',
        r':\s*([A-Z][A-Za-z0-9]+(?:\.[A-Za-z]+)?)\s+[Rr]aises',
        r'([A-Z][A-Za-z0-9]+)\s+[Rr]aises\s+[€\$£]',
    ]

    for pattern in patterns:
        match = re.search(pattern, title)
        if match:
            company = match.group(1).strip()
            if len(company) > 2 and company not in ["The", "This", "How", "Why", "What", "New"]:
                break

    if company == "Unknown":
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                company = match.group(1).strip()
                if len(company) > 2 and company not in ["The", "This", "How", "Why", "What", "New"]:
                    break

    # Extract amount
    amount = ""
    amount_match = re.search(r'[€\$£](\d+(?:\.\d+)?)\s*(?:million|M|billion|B)', text, re.IGNORECASE)
    if amount_match:
        num = float(amount_match.group(1))
        currency = "€" if "€" in text[:text.find(amount_match.group(0))+20] else "$"
        if 'billion' in text.lower():
            amount = f"{currency}{num}B"
        else:
            amount = f"{currency}{num}M"

    # Extract round type
    round_type = ""
    text_lower = text.lower()
    for rt in ["series a", "series b", "series c", "series d", "seed", "pre-seed"]:
        if rt in text_lower:
            round_type = rt.title()
            break

    # Detect region
    detected_region = "us"
    for region, config in REGIONS.items():
        for country in config["countries"]:
            if country.lower() in text_lower:
                detected_region = region
                break

    return {
        "company": company,
        "amount": amount,
        "round_type": round_type,
        "detected_region": detected_region,
        "article_url": url,
        "article_title": title,
        "article_content": content[:800],
    }


def find_decision_makers_exa(company: str, max_members: int = 10) -> list:
    """Find all decision makers (CEO, CTO, HR, COO, VPs, founders) using Exa with multiple search strategies."""
    api_key = get_exa_api_key()
    if not api_key:
        print("[WARN] EXA_API_KEY not found")
        return []

    team_members = []
    seen_names = set()

    # Strategy 1: Search for LinkedIn PROFILES specifically (not posts)
    # Priority: CEO, CTO, Head of HR first, then other leadership
    linkedin_queries = [
        f'site:linkedin.com/in/ "{company}" CEO',
        f'site:linkedin.com/in/ "{company}" CTO',
        f'site:linkedin.com/in/ "{company}" head of people',
        f'site:linkedin.com/in/ "{company}" head of talent',
        f'site:linkedin.com/in/ "{company}" founder',
        f'site:linkedin.com/in/ "{company}" COO',
        f'site:linkedin.com/in/ "{company}" VP engineering',
        f'site:linkedin.com/in/ "{company}" head of engineering',
    ]

    for query in linkedin_queries:
        if len(team_members) >= max_members:
            break

        try:
            response = requests.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": query,
                    "type": "keyword",  # Use keyword search for site: queries
                    "numResults": 10,
                },
                timeout=30
            )

            if response.ok:
                for r in response.json().get("results", []):
                    url = r.get("url", "")
                    title = r.get("title", "")

                    # ONLY accept profile URLs, not posts/activities
                    if "linkedin.com/in/" in url and "/posts/" not in url and "/activity" not in url:
                        # 3-priority name resolution
                        # Priority 1: Extract from LinkedIn page title (free)
                        name = extract_name_from_linkedin_title(title, company)

                        if not name:
                            # Priority 2: Clean URL slug (strip ID suffixes)
                            name_part = url.split("/in/")[1].split("/")[0].split("?")[0]
                            raw_name = name_part.replace("-", " ").title()
                            name_info = clean_linkedin_name(raw_name)
                            name = name_info["cleaned_name"]

                            # Priority 3: Resolve handles via Tavily ($0.005/call)
                            if name_info["needs_resolution"]:
                                print(f"      [NAME] Handle detected: '{name}' - resolving via Tavily...")
                                name = resolve_name_via_tavily(name, company, url)

                        if name in seen_names or len(name) < 3:
                            continue

                        # Determine role from title
                        role = "Executive"
                        title_lower = title.lower()
                        if "ceo" in title_lower or "chief executive" in title_lower:
                            role = "CEO"
                        elif "cto" in title_lower or "chief technology" in title_lower:
                            role = "CTO"
                        elif "founder" in title_lower or "co-founder" in title_lower:
                            role = "Founder"
                        elif "people" in title_lower or "hr" in title_lower or "talent" in title_lower:
                            role = "Head of People"
                        elif "coo" in title_lower or "operations" in title_lower:
                            role = "COO"

                        seen_names.add(name)
                        team_members.append({
                            "name": name,
                            "role": role,
                            "linkedin_url": url,
                        })
                        print(f"      [FOUND] {name} - {role}")

            time.sleep(0.3)

        except Exception as e:
            print(f"[WARN] Exa search failed: {e}")

    # Strategy 2: Neural search with broader terms
    if len(team_members) < max_members:
        broader_queries = [
            f"{company} startup CEO LinkedIn profile",
            f"{company} company CTO founder LinkedIn",
        ]

        for query in broader_queries:
            if len(team_members) >= max_members:
                break

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
                    },
                    timeout=30
                )

                if response.ok:
                    for r in response.json().get("results", []):
                        if len(team_members) >= max_members:
                            break

                        url = r.get("url", "")
                        title = r.get("title", "")

                        # Only profile URLs
                        if "linkedin.com/in/" in url and "/posts/" not in url and "/activity" not in url:
                            # 3-priority name resolution (same as Strategy 1)
                            name = extract_name_from_linkedin_title(title, company)

                            if not name:
                                name_part = url.split("/in/")[1].split("/")[0].split("?")[0]
                                raw_name = name_part.replace("-", " ").title()
                                name_info = clean_linkedin_name(raw_name)
                                name = name_info["cleaned_name"]

                                if name_info["needs_resolution"]:
                                    print(f"      [NAME] Handle detected: '{name}' - resolving via Tavily...")
                                    name = resolve_name_via_tavily(name, company, url)

                            if name in seen_names or len(name) < 3:
                                continue

                            role = "Founder"
                            title_lower = title.lower()
                            if "ceo" in title_lower:
                                role = "CEO"
                            elif "cto" in title_lower:
                                role = "CTO"

                            seen_names.add(name)
                            team_members.append({
                                "name": name,
                                "role": role,
                                "linkedin_url": url,
                            })
                            print(f"      [FOUND] {name} - {role}")

                time.sleep(0.3)

            except Exception as e:
                print(f"[WARN] Exa neural search failed: {e}")

    # Strategy 3: Search Crunchbase/TheOrg for team info
    if len(team_members) < max_members:
        try:
            response = requests.post(
                "https://api.exa.ai/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "query": f"{company} team founders leadership",
                    "type": "neural",
                    "numResults": 10,
                    "includeDomains": ["crunchbase.com", "theorg.com", "pitchbook.com"],
                },
                timeout=30
            )

            if response.ok:
                for r in response.json().get("results", []):
                    if len(team_members) >= max_members:
                        break

                    title = r.get("title", "")
                    text = r.get("text", "") or ""
                    combined = title + " " + text

                    # Extract name-role patterns
                    for target_role in ["CEO", "CTO", "Founder", "Co-Founder", "COO"]:
                        patterns = [
                            rf'([A-Z][a-z]+\s+[A-Z][a-z]+)\s*[-,]\s*{target_role}',
                            rf'{target_role}[:\s]+([A-Z][a-z]+\s+[A-Z][a-z]+)',
                        ]
                        for pattern in patterns:
                            matches = re.findall(pattern, combined, re.IGNORECASE)
                            for found_name in matches:
                                if found_name not in seen_names and len(team_members) < max_members:
                                    # Skip generic words
                                    if found_name.lower() in ["the company", "our team", "this page"]:
                                        continue
                                    seen_names.add(found_name)
                                    team_members.append({
                                        "name": found_name,
                                        "role": target_role,
                                        "linkedin_url": "",
                                    })
                                    print(f"      [FOUND] {found_name} - {target_role}")

        except Exception as e:
            print(f"[WARN] Exa team search failed: {e}")

    return team_members


def create_gmail_draft(email_data: dict, company_info: dict, recipient_email: str, target: str = "florian") -> str:
    """Create a Gmail draft."""
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build
    except ImportError:
        print("[ERROR] Google API packages not installed")
        return None

    token_path = GMAIL_TOKENS.get(target)
    if not token_path or not token_path.exists():
        # Fallback
        for path in GMAIL_TOKENS.values():
            if path and path.exists():
                token_path = path
                break

    if not token_path:
        print("[ERROR] Gmail token not found")
        return None

    print(f"      [Gmail] Using token: {token_path.name}")

    creds = Credentials.from_authorized_user_file(str(token_path))

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        with open(token_path, 'w') as f:
            f.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)

    to_email = email_data.get("to_email") or recipient_email

    msg = MIMEMultipart('alternative')
    msg['To'] = to_email
    msg['Subject'] = email_data['subject']

    # Clean email body (no research bundled - just the email)
    body = email_data['body']

    msg.attach(MIMEText(body, 'plain'))

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()

    try:
        draft = service.users().drafts().create(
            userId='me',
            body={'message': {'raw': raw}}
        ).execute()
        return draft.get('id')
    except Exception as e:
        print(f"[ERROR] Failed to create draft: {e}")
        return None


def run_mvp_workflow(
    region: str = "us",
    limit: int = 1,
    days_back: int = 7,
    dry_run: bool = False,
    create_drafts: bool = False,
    gmail_target: str = "florian",
):
    """
    Main MVP workflow.

    1. Find funding announcements
    2. Find decision makers
    3. Enrich with all social channels + personal signals
    4. Generate SEPARATE research report
    5. Generate SEPARATE email drafts
    6. Create Gmail drafts (optional)
    """
    print("\n" + "="*70)
    print("JORGE MVP ORCHESTRATOR")
    print("="*70)
    print(f"Region: {region.upper()} | Limit: {limit} companies | Days: {days_back}")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE'}")
    if create_drafts:
        print(f"Drafts to: {gmail_target.upper()}'s Gmail")
    print("="*70 + "\n")

    seen_data = load_seen()
    seen_companies = set(seen_data.get("companies", {}).keys())

    language = REGIONS.get(region, {}).get("language", "en")
    recipient_email = os.environ.get("NOTIFICATION_EMAIL", "")

    # Step 1: Search for funding
    print("\n[STEP 1] Searching for funding announcements...")
    results = search_funding_tavily(region=region, limit=limit * 3, days_back=days_back)

    processed = []
    drafts_created = 0

    for result in results:
        if len(processed) >= limit:
            break

        company_info = extract_company_info(result)
        company = company_info["company"]

        if company == "Unknown" or company.lower() in seen_companies:
            continue

        print(f"\n{'='*70}")
        print(f"[COMPANY] {company}")
        print(f"{'='*70}")
        print(f"   Amount: {company_info['amount'] or 'N/A'}")
        print(f"   Round: {company_info['round_type'] or 'N/A'}")
        print(f"   Region: {company_info['detected_region'].upper()}")
        print(f"   Article: {company_info['article_url'][:60]}...")

        # Mark as seen
        seen_data["companies"][company.lower()] = {
            "seen_at": datetime.now(timezone.utc).isoformat(),
            "amount": company_info["amount"],
            "region": region,
        }

        # Step 2: Find company website
        print(f"\n[STEP 2] Finding company website...")
        from jorge_person_enricher import find_company_website_exa
        company_website = find_company_website_exa(company)
        if company_website:
            company_info["company_website"] = company_website
            print(f"   [OK] Website: {company_website}")
        else:
            company_info["company_website"] = ""
            print(f"   [!] Website not found")

        # Step 2.5: Research feature focus for email personalization
        print(f"\n[STEP 2.5] Researching feature focus...")
        feature_focus = research_company_feature_focus(company, company_website)
        company_info["feature_focus"] = feature_focus
        print(f"   [OK] Feature focus: \"{feature_focus}\"")

        # Step 3: Find decision makers
        print(f"\n[STEP 3] Finding decision makers...")
        decision_makers = find_decision_makers_exa(company, max_members=10)

        if not decision_makers:
            print(f"   [!] No decision makers found - skipping")
            continue

        print(f"   Found {len(decision_makers)} decision makers")

        # Step 4: Enrich all decision makers
        print(f"\n[STEP 4] Enriching decision makers (social + email + personal signals)...")
        enriched_dms = enrich_all_decision_makers(company, decision_makers, company_website=company_website)

        # Step 4.5: Search for hiring signals
        print(f"\n[STEP 4.5] Searching for hiring signals...")
        hiring_signals = search_hiring_signals(company)
        if hiring_signals:
            print(f"   Found {len(hiring_signals)} hiring signals:")
            for hs in hiring_signals[:5]:
                print(f"      - {hs.get('role', 'N/A')} ({hs.get('level', 'N/A')}) - {hs.get('date_hint', 'Recent')}")
        else:
            print(f"   No hiring signals found")

        # Step 5: Generate research report (SEPARATE)
        print(f"\n[STEP 5] Generating research report...")
        report = generate_research_report(
            company_info=company_info,
            decision_makers=enriched_dms,
            hiring_signals=hiring_signals,
            save_to_file=True
        )

        # Step 6: Generate email drafts (SEPARATE)
        print(f"\n[STEP 6] Generating email drafts...")
        emails = generate_all_emails(
            company_info=company_info,
            decision_makers=enriched_dms,
            language=language,
            save_to_file=True
        )

        # Step 7: Create Gmail drafts
        if create_drafts and not dry_run:
            print(f"\n[STEP 7] Creating Gmail drafts...")
            for email_data in emails:
                draft_id = create_gmail_draft(
                    email_data=email_data,
                    company_info=company_info,
                    recipient_email=recipient_email,
                    target=gmail_target
                )
                if draft_id:
                    print(f"      [OK] Draft created for {email_data['to_name']} ({email_data['to_role']})")
                    drafts_created += 1
                else:
                    print(f"      [FAIL] Draft failed for {email_data['to_name']}")
        elif dry_run:
            print(f"\n[STEP 7] DRY RUN - would create {len(emails)} Gmail drafts")

        processed.append({
            "company": company,
            "amount": company_info["amount"],
            "round_type": company_info["round_type"],
            "decision_makers": [dm["name"] for dm in enriched_dms],
            "emails_generated": len(emails),
        })

    # Save seen
    save_seen(seen_data)

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("="*70)
    print(f"Companies processed: {len(processed)}")
    total_dms = sum(len(p.get('decision_makers', [])) for p in processed)
    print(f"Decision makers found: {total_dms}")
    print(f"Research reports generated: {len(processed)}")
    print(f"Email drafts generated: {sum(p.get('emails_generated', 0) for p in processed)}")
    if create_drafts:
        print(f"Gmail drafts created: {drafts_created}")
        print(f"\n[EMAIL] View drafts: https://mail.google.com/mail/#drafts")

    print(f"\n[FILES] Deep research: {TMP_DIR / 'deep_research'}")

    return processed


def run_single_company(
    company: str,
    amount: str = "",
    round_type: str = "",
    create_drafts: bool = False,
    gmail_target: str = "florian",
):
    """
    Run the full pipeline for a single named company.

    Usage:
        python execution/jorge_mvp_orchestrator.py --company "ElevenLabs" --amount "$500M" --round "Series D" --send
    """
    print("\n" + "="*70)
    print(f"JORGE MVP - SINGLE COMPANY: {company}")
    print("="*70)
    print(f"Amount: {amount or 'N/A'} | Round: {round_type or 'N/A'}")
    if create_drafts:
        print(f"Drafts to: {gmail_target.upper()}'s Gmail")
    print("="*70 + "\n")

    company_info = {
        "company": company,
        "amount": amount,
        "round_type": round_type,
        "article_url": "",
        "article_title": f"{company} raises {amount}",
        "article_content": "",
        "detected_region": "us",
    }

    # Step 2: Find company website
    print(f"[STEP 2] Finding company website...")
    from jorge_person_enricher import find_company_website_exa
    company_website = find_company_website_exa(company)
    if company_website:
        company_info["company_website"] = company_website
        print(f"   [OK] Website: {company_website}")
    else:
        company_info["company_website"] = ""
        print(f"   [!] Website not found")

    # Step 2.5: Research feature focus
    print(f"\n[STEP 2.5] Researching feature focus...")
    feature_focus = research_company_feature_focus(company, company_website)
    company_info["feature_focus"] = feature_focus
    print(f"   [OK] Feature focus: \"{feature_focus}\"")

    # Step 3: Find decision makers
    print(f"\n[STEP 3] Finding decision makers...")
    decision_makers = find_decision_makers_exa(company, max_members=10)

    if not decision_makers:
        print(f"   [!] No decision makers found")
        return []

    print(f"   Found {len(decision_makers)} decision makers:")
    for dm in decision_makers:
        print(f"      - {dm['name']} ({dm['role']})")

    # Step 4: Enrich all decision makers
    print(f"\n[STEP 4] Enriching decision makers (social + email + personal signals)...")
    enriched_dms = enrich_all_decision_makers(company, decision_makers, company_website=company_website)

    # Step 4.5: Search for hiring signals
    print(f"\n[STEP 4.5] Searching for hiring signals...")
    hiring_signals = search_hiring_signals(company)
    if hiring_signals:
        print(f"   Found {len(hiring_signals)} hiring signals:")
        for hs in hiring_signals[:5]:
            print(f"      - {hs.get('role', 'N/A')} ({hs.get('level', 'N/A')}) - {hs.get('date_hint', 'Recent')}")
    else:
        print(f"   No hiring signals found")

    # Step 5: Generate research report
    print(f"\n[STEP 5] Generating research report...")
    report = generate_research_report(
        company_info=company_info,
        decision_makers=enriched_dms,
        hiring_signals=hiring_signals,
        save_to_file=True
    )

    # Step 6: Generate email drafts
    print(f"\n[STEP 6] Generating email drafts...")
    emails = generate_all_emails(
        company_info=company_info,
        decision_makers=enriched_dms,
        language="en",
        save_to_file=True
    )

    # Step 7: Create Gmail drafts
    drafts_created = 0
    if create_drafts:
        print(f"\n[STEP 7] Creating Gmail drafts...")
        recipient_email = os.environ.get("NOTIFICATION_EMAIL", "")
        for email_data in emails:
            draft_id = create_gmail_draft(
                email_data=email_data,
                company_info=company_info,
                recipient_email=recipient_email,
                target=gmail_target
            )
            if draft_id:
                print(f"      [OK] Draft created for {email_data['to_name']} ({email_data['to_role']})")
                drafts_created += 1
            else:
                print(f"      [FAIL] Draft failed for {email_data['to_name']}")

    # Summary
    print(f"\n{'='*70}")
    print("SUMMARY")
    print("="*70)
    print(f"Company: {company}")
    print(f"Decision makers found: {len(enriched_dms)}")
    print(f"Email drafts generated: {len(emails)}")
    if create_drafts:
        print(f"Gmail drafts created: {drafts_created}")
        print(f"\n[EMAIL] View drafts: https://mail.google.com/mail/#drafts")
    print(f"\n[FILES] Deep research: {TMP_DIR / 'deep_research'}")

    return emails


def main():
    parser = argparse.ArgumentParser(description="Jorge MVP Orchestrator")

    # Single company mode
    parser.add_argument("--company", "-c", type=str, default=None,
                        help="Run pipeline for a specific company (e.g. 'ElevenLabs')")
    parser.add_argument("--amount", "-a", type=str, default="",
                        help="Funding amount (e.g. '$500M')")
    parser.add_argument("--round", type=str, default="",
                        help="Funding round (e.g. 'Series D')")

    # Search mode
    parser.add_argument("--region", "-r", choices=["us", "eu", "spain"], default="us",
                        help="Geographic region (default: us)")
    parser.add_argument("--limit", "-l", type=int, default=1,
                        help="Max companies to process (default: 1)")
    parser.add_argument("--days", "-d", type=int, default=7,
                        help="Search last N days (default: 7)")

    # Common
    parser.add_argument("--dry-run", action="store_true",
                        help="Preview without creating Gmail drafts")
    parser.add_argument("--send", action="store_true",
                        help="Create Gmail drafts")
    parser.add_argument("--target", "-t", choices=["florian", "jorge"], default="florian",
                        help="Which Gmail to draft to (default: florian)")

    args = parser.parse_args()

    # Check if jorge target but token doesn't exist
    if args.target == "jorge" and not GMAIL_TOKENS["jorge"].exists():
        print("[ERROR] Jorge's Gmail token not found!")
        print(f"        Expected: {GMAIL_TOKENS['jorge']}")
        print("\nTo authorize Jorge's Gmail:")
        print("  1. Run: python execution/auth_jorge_gmail.py")
        print("  2. Complete OAuth flow")
        exit(1)

    if args.company:
        # Single company mode
        run_single_company(
            company=args.company,
            amount=args.amount,
            round_type=args.round,
            create_drafts=args.send and not args.dry_run,
            gmail_target=args.target,
        )
    else:
        # Search mode
        run_mvp_workflow(
            region=args.region,
            limit=args.limit,
            days_back=args.days,
            dry_run=args.dry_run,
            create_drafts=args.send,
            gmail_target=args.target,
        )


if __name__ == "__main__":
    main()
