#!/usr/bin/env python3
"""
Jorge Research Report Generator

Generates a SEPARATE markdown research report for each company.
This is distinct from the email copy - research report is for Jorge's reference.

Output: .tmp/deep_research/{company}/research_report.md
"""

import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"
DEEP_RESEARCH_DIR = TMP_DIR / "deep_research"
PAIN_KB_FILE = PROJECT_ROOT / "Resources" / "founder_pain_seed.json"


def load_pain_kb() -> list:
    """Load founder pain quotes from KB."""
    if PAIN_KB_FILE.exists():
        try:
            with open(PAIN_KB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return []


def get_relevant_pain_quotes(industry: str = None, round_type: str = None, limit: int = 3) -> list:
    """Get relevant pain quotes from KB based on industry/round."""
    pain_kb = load_pain_kb()
    if not pain_kb:
        return []

    # For now, return top quotes (could be enhanced with semantic matching)
    quotes = []
    for item in pain_kb[:limit]:
        if isinstance(item, dict):
            quotes.append({
                "quote": item.get("quote", ""),
                "founder": item.get("founder", ""),
                "company": item.get("company", ""),
                "source": item.get("source", "")
            })
        elif isinstance(item, str):
            quotes.append({"quote": item, "founder": "Unknown", "company": "", "source": ""})

    return quotes


def generate_research_report(
    company_info: dict,
    decision_makers: list,
    hiring_signals: list = None,
    save_to_file: bool = True
) -> str:
    """
    Generate a comprehensive research report markdown.

    Args:
        company_info: Dict with company, amount, round_type, article_url, etc.
        decision_makers: List of enriched person dicts
        hiring_signals: Optional list of open roles/hiring data
        save_to_file: Whether to save to .tmp/research_reports/

    Returns:
        Markdown string of the research report
    """
    company = company_info.get("company", "Unknown")
    amount = company_info.get("amount", "N/A")
    round_type = company_info.get("round_type", "N/A")
    article_url = company_info.get("article_url", "")
    detected_region = company_info.get("detected_region", "US").upper()
    article_content = company_info.get("article_content", "")

    today = datetime.now().strftime("%Y-%m-%d")

    # Get all decision maker names for header
    dm_names = [dm.get("name", "Unknown") for dm in decision_makers if dm.get("name")]
    names_str = ", ".join(dm_names) if dm_names else "Unknown"

    # Get relevant pain quotes
    pain_quotes = get_relevant_pain_quotes(round_type=round_type, limit=3)

    # Get VC/investor data
    vc_firm = company_info.get("vc_firm", "")
    deal_partner = company_info.get("deal_partner", "")
    company_website = company_info.get("company_website", "")
    about_page_summary = company_info.get("about_page_summary", "")

    # Build markdown report
    md = f"""# RESEARCH REPORT: {company}
**Generated:** {today}
**Decision Makers:** {names_str}

---

## COMPANY SUMMARY

| Field | Value |
|-------|-------|
| **Company** | {company} |
| **Funding** | {amount} {round_type} |
| **Region** | {detected_region} |
| **Article** | [{article_url[:50]}...]({article_url}) |
| **Company Website** | {f'[{company_website}]({company_website})' if company_website else 'NEEDS ENRICHMENT'} |
| **VC Firm (Lead)** | {vc_firm if vc_firm else 'NEEDS ENRICHMENT'} |
| **Deal Partner** | {deal_partner if deal_partner else 'NEEDS ENRICHMENT'} |

"""

    if article_content:
        md += f"""### Article Excerpt
> {article_content[:500]}{'...' if len(article_content) > 500 else ''}

"""

    if about_page_summary:
        md += f"""### About Page Summary
{about_page_summary}

"""

    md += """---

## DECISION MAKERS

"""

    # Add each decision maker
    for i, dm in enumerate(decision_makers, 1):
        name = dm.get("name", "Unknown")
        role = dm.get("role", "Executive")
        email = dm.get("email", "")
        linkedin = dm.get("linkedin_url", "")
        twitter = dm.get("twitter_url", "")
        instagram = dm.get("instagram_url", "")
        facebook = dm.get("facebook_url", "")
        personal_signal = dm.get("personal_signal", {})

        md += f"""### {i}. {name} - {role}

| Channel | Link |
|---------|------|
| **Email** | {email if email else '`NEEDS ENRICHMENT`'} |
| **LinkedIn** | {f'[Profile]({linkedin})' if linkedin else 'Not found'} |
| **Twitter** | {f'[Profile]({twitter})' if twitter else 'Not found'} |
| **Instagram** | {f'[Profile]({instagram})' if instagram else 'Not found'} |
| **Facebook** | {f'[Profile]({facebook})' if facebook else 'Not found'} |

"""

        # Personal signal section
        if personal_signal and personal_signal.get("source"):
            md += f"""**Personal Signal for PS Line:**
- **Source:** {personal_signal.get('source', 'N/A')}
- **Summary:** {personal_signal.get('summary', 'N/A')}
- **PS Hook:** _{personal_signal.get('hook_for_ps', 'N/A')}_

"""
        else:
            md += """**Personal Signal:** _No recent public content found - use generic PS_

"""

    # Hiring signals section
    md += """---

## HIRING SIGNALS

"""
    if hiring_signals:
        md += "| Role | Level | Posted | Source |\n|------|-------|--------|--------|\n"
        for signal in hiring_signals:
            source = signal.get('source', 'N/A')
            # Truncate source URL for readability
            if len(source) > 40:
                source = source[:40] + "..."
            md += f"| {signal.get('role', 'N/A')} | {signal.get('level', 'N/A')} | {signal.get('date_hint', 'Recent')} | {source} |\n"
    else:
        md += "_No hiring signals captured - consider manual LinkedIn check_\n"

    # Pain quotes section
    md += """
---

## RELEVANT FOUNDER PAIN QUOTES

"""
    if pain_quotes:
        for pq in pain_quotes:
            quote = pq.get("quote", "")
            founder = pq.get("founder", "")
            company_name = pq.get("company", "")
            if quote:
                attribution = f"- {founder}"
                if company_name:
                    attribution += f", {company_name}"
                md += f'> "{quote}"\n{attribution}\n\n'
    else:
        md += "_No pain quotes loaded from KB_\n"

    # Recommended approach section
    md += f"""
---

## RECOMMENDED OUTREACH APPROACH

### Primary Hook
**Funding Timing:** Reference the {amount} {round_type} raise and the typical post-raise challenge of scaling the team quickly.

### Stakeholder Cross-Reference
Include in each email: "I also reached out to {' and '.join(dm_names[1:]) if len(dm_names) > 1 else 'your team'}..."

### Email Subject Line
`Re: {company}'s {amount} {round_type} - {', '.join([n.split()[0] for n in dm_names])}`

---

## NEXT STEPS

- [ ] Review decision maker profiles
- [ ] Verify email addresses (consider Apollo/Hunter if missing)
- [ ] Check LinkedIn for recent posts (PS personalization)
- [ ] Review generated email drafts
- [ ] Send or schedule outreach

---

_Report generated by Jorge MVP Orchestrator_
"""

    # Save to file if requested — each company gets its own folder
    if save_to_file:
        company_dir = DEEP_RESEARCH_DIR / company.replace(' ', '_')
        company_dir.mkdir(parents=True, exist_ok=True)
        filepath = company_dir / "research_report.md"

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"      [OK] Research report saved: {filepath}")

    return md


if __name__ == "__main__":
    # Test with sample data
    test_company = {
        "company": "Inferact",
        "amount": "$150M",
        "round_type": "Seed",
        "article_url": "https://techcrunch.com/example",
        "detected_region": "us",
        "article_content": "Inferact, the AI inference startup founded by the creators of vLLM, has raised $150M in seed funding..."
    }

    test_dms = [
        {
            "name": "Simon Mo",
            "role": "CEO",
            "email": "simon@inferact.ai",
            "linkedin_url": "https://linkedin.com/in/simonmo",
            "twitter_url": "https://twitter.com/simonmo",
            "instagram_url": "",
            "facebook_url": "",
            "personal_signal": {
                "source": "LinkedIn post, Jan 22, 2026",
                "summary": "Announced Inferact launch, excited about democratizing AI inference",
                "hook_for_ps": "Your post about 'making AI inference effortless' resonates"
            }
        },
        {
            "name": "Woosuk Kwon",
            "role": "CTO",
            "email": "",
            "linkedin_url": "https://linkedin.com/in/woosuk-kwon",
            "twitter_url": "",
            "instagram_url": "",
            "facebook_url": "",
            "personal_signal": {}
        }
    ]

    report = generate_research_report(test_company, test_dms)
    print("\n" + "="*60)
    print("SAMPLE RESEARCH REPORT:")
    print("="*60)
    print(report[:2000] + "...")
