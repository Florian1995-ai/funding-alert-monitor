#!/usr/bin/env python3
"""
Hybrid Funding Monitor - RSS + Tavily Fallback

TIER 1: RSS Feeds (FREE - just HTTP requests)
- TechCrunch, VentureBeat, GeekWire, SiliconANGLE
- AlleyWatch, LA TechWatch, dot.LA
- Built In network

TIER 2: Tavily API (for press wires without RSS)
- BusinessWire, PRNewswire, GlobeNewswire
- AccessWire, PRWeb, EIN Presswire
- VC News Daily, FinSMEs, The SaaS News

Automatically triggers:
1. Decision maker research
2. Deep research report
3. Email draft generation

Usage:
    python execution/funding_monitor_hybrid.py
    python execution/funding_monitor_hybrid.py --dry-run
    python execution/funding_monitor_hybrid.py --run-pipeline
"""

import os
import sys
import json
import hashlib
import argparse
import re
import requests
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

try:
    import feedparser
except ImportError:
    print("ERROR: feedparser not installed. Run: pip install feedparser")
    sys.exit(1)

from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent

# ============================================================================
# TIER 1: RSS FEEDS (FREE)
# ============================================================================

RSS_FEEDS = [
    # === Tech Media (High Signal) ===
    {"name": "TechCrunch Funding", "url": "https://techcrunch.com/tag/funding/feed/", "priority": 1},
    {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/feed/", "priority": 1},
    {"name": "VentureBeat", "url": "https://venturebeat.com/category/business/feed/", "priority": 1},
    {"name": "SiliconANGLE", "url": "https://siliconangle.com/feed/", "priority": 1},
    {"name": "GeekWire", "url": "https://www.geekwire.com/feed/", "priority": 2},

    # === Regional (NYC, LA, Seattle) ===
    {"name": "AlleyWatch NYC", "url": "https://www.alleywatch.com/feed/", "priority": 2},
    {"name": "dot.LA", "url": "https://dot.la/feed", "priority": 2},

    # === Built In Network ===
    {"name": "Built In", "url": "https://builtin.com/feed", "priority": 3},
    {"name": "Built In NYC", "url": "https://www.builtinnyc.com/feed", "priority": 3},
    {"name": "Built In SF", "url": "https://www.builtinsf.com/feed", "priority": 3},
    {"name": "Built In Seattle", "url": "https://www.builtinseattle.com/feed", "priority": 3},
    {"name": "Built In LA", "url": "https://www.builtinla.com/feed", "priority": 3},
    {"name": "Built In Chicago", "url": "https://www.builtinchicago.org/feed", "priority": 3},

    # === Press Wires (some have RSS) ===
    {"name": "PRNewswire Tech", "url": "https://www.prnewswire.com/rss/technology-latest-news/technology-latest-news-list.rss", "priority": 2},
    {"name": "GlobeNewswire", "url": "https://www.globenewswire.com/RssFeed/subjectcode/23-Funding%20and%20Investment/feedTitle/GlobeNewswire%20-%20Funding%20and%20Investment", "priority": 2},

    # === Crunchbase News ===
    {"name": "Crunchbase News", "url": "https://news.crunchbase.com/feed/", "priority": 1},
]

# ============================================================================
# TIER 2: TAVILY FALLBACK (for sources without RSS)
# ============================================================================

TAVILY_DOMAINS = [
    # Press wires without good RSS feeds
    "businesswire.com",
    "accesswire.com",
    "accessnewswire.com",
    "prweb.com",
    "einpresswire.com",
    "newswire.com",

    # Funding aggregators
    "vcnewsdaily.com",
    "thesaasnews.com",
    "finsmes.com",

    # Startup-focused wires
    "startupnewswire.com",
]

TAVILY_QUERIES = [
    '"raises" "million" funding startup',
    '"secures" "funding" "Series A" OR "Series B"',
    '"announced today" "raises" "million"',
    '"seed funding" "platform" "AI" OR "SaaS"',
]

# ============================================================================
# FUNDING DETECTION
# ============================================================================

FUNDING_KEYWORDS = [
    "series a", "series b", "series c", "series d", "series e",
    "seed round", "seed funding", "pre-seed",
    "raises", "raised", "secures", "secured",
    "funding round", "funding announcement",
    "million in funding", "million funding",
    "venture capital", "investment round",
]

# US State detection for location filtering
US_STATES = [
    "CA", "NY", "MA", "TX", "WA", "CO", "IL", "GA", "FL", "NC",
    "PA", "OH", "AZ", "VA", "OR", "NV", "UT", "MN", "TN", "MD",
]

# ============================================================================
# STATE MANAGEMENT
# ============================================================================

SEEN_FILE = PROJECT_ROOT / ".tmp" / "seen_funding_hybrid.json"


def load_seen() -> dict:
    """Load previously seen articles."""
    if SEEN_FILE.exists():
        try:
            with open(SEEN_FILE, 'r') as f:
                data = json.load(f)
                # Clean entries older than 14 days
                cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
                data["articles"] = {
                    k: v for k, v in data.get("articles", {}).items()
                    if v.get("seen_at", "") > cutoff
                }
                return data
        except Exception:
            pass
    return {"articles": {}, "last_run": None}


def save_seen(data: dict):
    """Save seen articles."""
    SEEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    data["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(SEEN_FILE, 'w') as f:
        json.dump(data, f, indent=2)


def get_article_id(url: str, title: str = "") -> str:
    """Generate unique ID for an article."""
    identifier = url or title
    return hashlib.md5(identifier.encode()).hexdigest()[:16]


# ============================================================================
# RSS FEED PROCESSING
# ============================================================================

def is_funding_article(title: str, summary: str) -> tuple[bool, str]:
    """Check if article is about funding."""
    text = (title + " " + summary).lower()

    for keyword in FUNDING_KEYWORDS:
        if keyword in text:
            return True, keyword

    return False, ""


def extract_funding_amount(text: str) -> str:
    """Extract funding amount from text."""
    text_lower = text.lower()

    patterns = [
        r'\$(\d+(?:\.\d+)?)\s*(?:billion|b)\b',
        r'\$(\d+(?:\.\d+)?)\s*(?:million|m|mn)\b',
        r'(\d+(?:\.\d+)?)\s*(?:billion|b)\s*(?:dollars?|usd)',
        r'(\d+(?:\.\d+)?)\s*(?:million|m|mn)\s*(?:dollars?|usd)',
        r'raises?\s*\$(\d+(?:\.\d+)?)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = float(match.group(1))
            if 'billion' in text_lower[max(0, match.start()-5):match.end()+15]:
                return f"${amount}B"
            return f"${amount}M"

    return ""


def extract_company_name(title: str) -> str:
    """Extract company name from title."""
    patterns = [
        r'^([^,\-:]+?)(?:\s+raises|\s+secures|\s+closes|\s+announces)',
        r'^([^,\-:]+?)(?:\s+lands|\s+gets|\s+nabs)',
    ]

    for pattern in patterns:
        match = re.match(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1).strip()

    for sep in [' raises', ' secures', ' - ', ': ', ', ']:
        if sep in title.lower():
            return title.split(sep)[0].strip()

    return title[:60]


def extract_round_type(text: str) -> str:
    """Extract funding round type."""
    text_lower = text.lower()

    rounds = [
        ("pre-seed", "Pre-Seed"),
        ("seed round", "Seed"),
        ("seed funding", "Seed"),
        ("series a", "Series A"),
        ("series b", "Series B"),
        ("series c", "Series C"),
        ("series d", "Series D"),
        ("series e", "Series E"),
        ("growth round", "Growth"),
    ]

    for pattern, label in rounds:
        if pattern in text_lower:
            return label

    return ""


def fetch_rss_feeds(max_age_hours: int = 48) -> list[dict]:
    """Fetch funding articles from RSS feeds."""
    seen_data = load_seen()
    seen_ids = set(seen_data.get("articles", {}).keys())
    cutoff_time = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)

    articles = []

    print(f"\n[RSS] Checking {len(RSS_FEEDS)} feeds...")

    for feed_info in sorted(RSS_FEEDS, key=lambda x: x["priority"]):
        feed_name = feed_info["name"]
        feed_url = feed_info["url"]

        try:
            print(f"  [{feed_name}]", end=" ")
            feed = feedparser.parse(feed_url, request_headers={'User-Agent': 'Mozilla/5.0'})

            if feed.bozo and not feed.entries:
                print(f"[SKIP] Parse error")
                continue

            count = 0
            for entry in feed.entries:
                title = entry.get("title", "")
                link = entry.get("link", "")
                summary = entry.get("summary", "")[:500]

                article_id = get_article_id(link, title)

                if article_id in seen_ids:
                    continue

                is_funding, matched_kw = is_funding_article(title, summary)
                if not is_funding:
                    continue

                # Parse date
                pub_date = None
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

                if pub_date and pub_date < cutoff_time:
                    continue

                articles.append({
                    "id": article_id,
                    "company": extract_company_name(title),
                    "amount": extract_funding_amount(title + " " + summary),
                    "round": extract_round_type(title + " " + summary),
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source": feed_name,
                    "source_type": "rss",
                    "matched_keyword": matched_kw,
                    "published": pub_date.isoformat() if pub_date else "",
                })

                seen_data["articles"][article_id] = {
                    "seen_at": datetime.now(timezone.utc).isoformat(),
                    "title": title[:100],
                }
                count += 1

            print(f"[OK] {count} new")

        except Exception as e:
            print(f"[FAIL] {str(e)[:50]}")

    save_seen(seen_data)
    return articles


# ============================================================================
# TAVILY FALLBACK
# ============================================================================

def get_tavily_api_key() -> Optional[str]:
    """Get Tavily API key from environment."""
    keys = [
        os.environ.get("TAVILY_API_KEY"),
        os.environ.get("TAVILY_API_KEY_2"),
        os.environ.get("TAVILY_API_KEY_3"),
    ]
    return next((k for k in keys if k), None)


def fetch_tavily_articles(max_age_days: int = 7) -> list[dict]:
    """Fetch funding articles from Tavily API."""
    api_key = get_tavily_api_key()
    if not api_key:
        print("\n[TAVILY] No API key found - skipping")
        return []

    seen_data = load_seen()
    seen_ids = set(seen_data.get("articles", {}).keys())

    articles = []

    print(f"\n[TAVILY] Searching {len(TAVILY_DOMAINS)} domains...")

    for query in TAVILY_QUERIES[:2]:  # Limit queries to save API credits
        try:
            print(f"  Query: {query[:50]}...", end=" ")

            response = requests.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_domains": TAVILY_DOMAINS,
                    "max_results": 20,
                    "include_raw_content": False,
                },
                timeout=30
            )

            if not response.ok:
                print(f"[FAIL] {response.status_code}")
                continue

            results = response.json().get("results", [])
            count = 0

            for r in results:
                url = r.get("url", "")
                title = r.get("title", "")
                content = r.get("content", "")[:500]

                article_id = get_article_id(url, title)

                if article_id in seen_ids:
                    continue

                is_funding, matched_kw = is_funding_article(title, content)
                if not is_funding:
                    continue

                articles.append({
                    "id": article_id,
                    "company": extract_company_name(title),
                    "amount": extract_funding_amount(title + " " + content),
                    "round": extract_round_type(title + " " + content),
                    "title": title,
                    "url": url,
                    "summary": content,
                    "source": "Tavily",
                    "source_type": "tavily",
                    "matched_keyword": matched_kw,
                    "published": "",
                })

                seen_data["articles"][article_id] = {
                    "seen_at": datetime.now(timezone.utc).isoformat(),
                    "title": title[:100],
                }
                count += 1

            print(f"[OK] {count} new")

        except Exception as e:
            print(f"[FAIL] {str(e)[:50]}")

    save_seen(seen_data)
    return articles


# ============================================================================
# PIPELINE INTEGRATION
# ============================================================================

def run_pipeline_for_company(company_info: dict) -> dict:
    """Run the full pipeline for a single company."""
    # Import pipeline components
    sys.path.insert(0, str(PROJECT_ROOT / "execution"))

    try:
        from jorge_person_enricher import (
            enrich_all_decision_makers,
            search_hiring_signals,
            research_company_feature_focus,
            find_company_website_exa,
        )
        from jorge_mvp_orchestrator import find_decision_makers_exa
        from jorge_research_report import generate_research_report
        from jorge_email_generator import generate_all_emails
    except ImportError as e:
        print(f"[WARN] Pipeline import failed: {e}")
        return {"error": str(e)}

    company = company_info["company"]
    amount = company_info["amount"]
    round_type = company_info.get("round", "")
    article_url = company_info["url"]

    print(f"\n{'='*60}")
    print(f"PIPELINE: {company}")
    print(f"{'='*60}")

    result = {
        "company": company,
        "amount": amount,
        "round": round_type,
        "article_url": article_url,
    }

    # Step 1: Find company website
    print(f"\n[1/6] Finding company website...")
    try:
        website = find_company_website_exa(company)
        result["website"] = website or ""
        print(f"      Website: {website or 'Not found'}")
    except Exception as e:
        result["website"] = ""
        print(f"      [WARN] {e}")

    # Step 2: Research feature focus
    print(f"\n[2/6] Researching feature focus...")
    try:
        feature_focus = research_company_feature_focus(
            company,
            result.get("website", ""),
            company_info.get("summary", "")
        )
        result["feature_focus"] = feature_focus
        print(f"      Feature: \"{feature_focus}\"")
    except Exception as e:
        result["feature_focus"] = "accelerate your roadmap"
        print(f"      [WARN] {e}")

    # Step 3: Find decision makers
    print(f"\n[3/6] Finding decision makers...")
    try:
        decision_makers = find_decision_makers_exa(company, max_members=3)
        if not decision_makers:
            decision_makers = [{"name": "NEEDS RESEARCH", "role": "CEO & Founder", "linkedin_url": ""}]
        result["decision_makers_found"] = len(decision_makers)
        for dm in decision_makers:
            print(f"      - {dm.get('name', 'Unknown')} ({dm.get('role', 'Unknown')})")
    except Exception as e:
        decision_makers = [{"name": "NEEDS RESEARCH", "role": "CEO & Founder", "linkedin_url": ""}]
        print(f"      [WARN] {e}")

    # Step 4: Enrich decision makers
    print(f"\n[4/6] Enriching decision makers...")
    try:
        enriched_dms = enrich_all_decision_makers(
            company,
            decision_makers,
            company_website=result.get("website", "")
        )
    except Exception as e:
        enriched_dms = decision_makers
        print(f"      [WARN] {e}")

    # Step 5: Search hiring signals
    print(f"\n[5/6] Searching hiring signals...")
    try:
        hiring_signals = search_hiring_signals(company)
        result["hiring_signals"] = len(hiring_signals)
        print(f"      Found {len(hiring_signals)} hiring signals")
    except Exception as e:
        hiring_signals = []
        print(f"      [WARN] {e}")

    # Prepare company info for report/emails
    full_company_info = {
        "company": company,
        "amount": amount,
        "round_type": round_type,
        "article_url": article_url,
        "article_content": company_info.get("summary", ""),
        "company_website": result.get("website", ""),
        "feature_focus": result.get("feature_focus", "accelerate your roadmap"),
        "detected_region": "US",
    }

    # Step 6: Generate research report
    print(f"\n[6/6] Generating research report...")
    try:
        report = generate_research_report(
            company_info=full_company_info,
            decision_makers=enriched_dms,
            hiring_signals=hiring_signals,
            save_to_file=True
        )
        result["report_generated"] = True
    except Exception as e:
        print(f"      [WARN] Report failed: {e}")
        result["report_generated"] = False

    # Step 7: Generate email drafts
    print(f"\n[7/7] Generating email drafts...")
    try:
        emails = generate_all_emails(
            company_info=full_company_info,
            decision_makers=enriched_dms,
            language="en",
            save_to_file=True
        )
        result["emails_generated"] = len(emails)
        print(f"      Generated {len(emails)} email drafts")
    except Exception as e:
        print(f"      [WARN] Emails failed: {e}")
        result["emails_generated"] = 0

    return result


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser(description="Hybrid Funding Monitor (RSS + Tavily)")
    parser.add_argument("--dry-run", action="store_true", help="Don't run pipeline, just show results")
    parser.add_argument("--run-pipeline", action="store_true", help="Run full pipeline for each company")
    parser.add_argument("--hours", type=int, default=48, help="Max age of articles in hours")
    parser.add_argument("--limit", type=int, default=5, help="Max companies to process")
    parser.add_argument("--output", "-o", help="Save results to JSON file")

    args = parser.parse_args()

    print("=" * 70)
    print("HYBRID FUNDING MONITOR")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"Mode: {'Dry Run' if args.dry_run else 'Pipeline' if args.run_pipeline else 'Discovery'}")

    # Fetch from RSS feeds (FREE)
    rss_articles = fetch_rss_feeds(max_age_hours=args.hours)

    # Fetch from Tavily (API cost)
    tavily_articles = fetch_tavily_articles()

    # Combine and deduplicate
    all_articles = rss_articles + tavily_articles
    seen_companies = set()
    unique_articles = []

    for article in all_articles:
        company_lower = article["company"].lower()
        if company_lower not in seen_companies and len(company_lower) > 2:
            seen_companies.add(company_lower)
            unique_articles.append(article)

    # Sort by amount (largest first)
    def parse_amount(a):
        amt = a.get("amount", "")
        if not amt:
            return 0
        try:
            num = float(re.search(r'[\d.]+', amt).group())
            if 'B' in amt:
                return num * 1000
            return num
        except:
            return 0

    unique_articles.sort(key=parse_amount, reverse=True)

    print(f"\n{'='*70}")
    print(f"RESULTS: {len(unique_articles)} unique funding announcements")
    print("=" * 70)

    if not unique_articles:
        print("No new funding announcements found.")
        return

    # Display results
    for i, article in enumerate(unique_articles[:15], 1):
        amount = f" | {article['amount']}" if article['amount'] else ""
        round_type = f" | {article['round']}" if article.get('round') else ""
        print(f"\n{i}. {article['company']}{amount}{round_type}")
        print(f"   Source: {article['source']} ({article['source_type']})")
        print(f"   URL: {article['url'][:70]}...")

    if len(unique_articles) > 15:
        print(f"\n... and {len(unique_articles) - 15} more")

    # Save to file
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(unique_articles, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to {output_path}")

    # Run pipeline
    if args.run_pipeline and not args.dry_run:
        print(f"\n{'='*70}")
        print(f"RUNNING PIPELINE FOR TOP {args.limit} COMPANIES")
        print("=" * 70)

        results = []
        for article in unique_articles[:args.limit]:
            result = run_pipeline_for_company(article)
            results.append(result)

        # Summary
        print(f"\n{'='*70}")
        print("PIPELINE SUMMARY")
        print("=" * 70)
        for r in results:
            status = "OK" if r.get("emails_generated", 0) > 0 else "NEEDS RESEARCH"
            print(f"  {r['company']}: {status}")

        # Save results
        results_path = PROJECT_ROOT / ".tmp" / f"pipeline_results_{datetime.now().strftime('%Y-%m-%d')}.json"
        with open(results_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nPipeline results saved to: {results_path}")

    elif args.dry_run:
        print("\n[DRY RUN] Would process these companies through pipeline")


if __name__ == "__main__":
    main()
