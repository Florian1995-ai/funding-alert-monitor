#!/usr/bin/env python3
"""
Jorge Email Generator

Generates SEPARATE email copy (distinct from research report) with:
- Subject line including all 3 decision maker names
- Cross-reference to other stakeholders ("I also reached out to...")
- Highly personalized PS line based on personal signal
- Role-specific angles (CEO vs CTO vs HR)

Output: .tmp/deep_research/{company}/email_drafts/{role}_{name}_{date}.md
"""

import os
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote
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


def get_founder_pain_quote() -> dict:
    """Get a founder pain quote with REAL attribution for email body."""
    pain_kb = load_pain_kb()
    if not pain_kb:
        # Fallback quote with real attribution
        return {
            "quote": "Hiring is one of those things where doing it well requires just an unbelievable amount of time. And I used the word unbelievable. Meaning like people literally won't believe you when you tell them how much time you spend recruiting.",
            "founder": "Jack Altman",
            "company": "Lattice",
            "source": "First Round Review podcast"
        }

    # Return first quote with proper field mapping
    item = pain_kb[0] if pain_kb else {}
    if isinstance(item, dict):
        # Get founder name - try founder_name first (from KB), then founder
        founder = item.get("founder_name", "") or item.get("founder", "")
        # Skip anonymous/unknown founders - use next quote with real name
        if not founder or founder.lower() in ["anonymous", "unknown", ""]:
            for q in pain_kb:
                if isinstance(q, dict):
                    f = q.get("founder_name", "") or q.get("founder", "")
                    if f and f.lower() not in ["anonymous", "unknown", ""]:
                        item = q
                        founder = f
                        break

        # Get source - prefer video_title, then source_url
        source = item.get("video_title", "") or item.get("source_url", "") or "a recent podcast"

        return {
            "quote": item.get("quote", ""),
            "founder": founder,
            "company": item.get("company", ""),
            "source": source
        }
    elif isinstance(item, str):
        return {"quote": item, "founder": "Jack Altman", "company": "Lattice", "source": "First Round Review podcast"}
    return {"quote": "", "founder": "", "company": "", "source": ""}


def decode_name(name: str) -> str:
    """URL-decode a name (e.g. 'Nicol%C3%B2' -> 'Nicolò')."""
    if not name:
        return name
    return unquote(name)


def get_first_name(full_name: str) -> str:
    """Extract first name from full name, URL-decoded."""
    if not full_name or full_name.lower() in ["there", "unknown"]:
        return "there"
    decoded = decode_name(full_name)
    return decoded.split()[0]


def get_cross_reference_names(decision_makers: list, exclude_name: str) -> list:
    """Get names of other decision makers (for cross-reference in email)."""
    other_names = []
    for dm in decision_makers:
        name = dm.get("name", "")
        if name and name.lower() not in ["there", "unknown"] and name != exclude_name:
            other_names.append(get_first_name(name))
    return other_names


def get_team_estimate(amount: str) -> str:
    """Calculate team estimate based on funding amount."""
    if not amount:
        return "a small dev team"

    import re
    match = re.search(r'(\d+(?:\.\d+)?)', amount)
    if not match:
        return "a dev team"

    num = float(match.group(1))

    if 'B' in amount.upper():
        return "a full engineering org (multiple pods)"

    # Millions
    if num < 3:
        return "1-2 senior devs"
    elif num < 10:
        return "2-3 senior devs + PM"
    elif num < 20:
        return "a full pod (3 devs + PM + tech lead)"
    else:
        return "multiple dev pods"


def get_role_category(role: str) -> str:
    """Map specific role to email template category."""
    role_lower = role.lower()

    if any(x in role_lower for x in ["ceo", "chief executive"]):
        return "CEO"
    elif any(x in role_lower for x in ["cto", "chief technology", "vp engineer", "head of engineer"]):
        return "CTO"
    elif any(x in role_lower for x in ["hr", "people", "talent", "recruiting"]):
        return "HR"
    elif any(x in role_lower for x in ["coo", "chief operating", "operations"]):
        return "COO"
    else:
        return "Founder"


def generate_subject_line(company: str, amount: str, round_type: str, other_first_names: list, recipient_first_name: str = "") -> str:
    """
    Generate subject line with up to 4 names: max 3 others + recipient LAST.

    Examples:
        4 names: "Mati, Siddharth, Emilie, Piotr - Congratulations on $500M raise"
        2 names: "Mati, Piotr - Congratulations on $500M raise"
        1 name:  "Piotr - Congratulations on $500M raise"
    """
    # Build names list: up to 3 others + recipient last
    subject_names = []
    if other_first_names:
        subject_names = other_first_names[:3]  # Max 3 others
    if recipient_first_name:
        subject_names.append(recipient_first_name)

    name_str = ", ".join(subject_names) if subject_names else ""

    if name_str:
        if amount:
            subject = f"{name_str} - Congratulations on {amount} raise"
        else:
            subject = f"{name_str} - Congratulations on your funding round"
    else:
        if amount:
            subject = f"Congratulations on {company}'s {amount} raise"
        else:
            subject = f"Congratulations on {company}'s funding round"

    return subject


def generate_cross_reference_line(other_names: list, feature_focus: str = "") -> str:
    """
    Generate the cross-reference line for the email body.

    Example: "I just wanted to reach out to see if Kelly, Ashish, and you have already considered..."
    The addressed person is replaced with "you" at the end.

    Args:
        other_names: Names of other decision makers
        feature_focus: Dynamic feature from company research (e.g., "build out your AI inference pipeline")
    """
    # Default feature focus if none provided
    if not feature_focus:
        feature_focus = "accelerate your roadmap"

    if not other_names:
        return f"I just wanted to reach out to see if you have already considered bringing on external dev support to {feature_focus} post-raise."

    if len(other_names) == 1:
        return f"I just wanted to reach out to see if {other_names[0]} and you have already considered bringing on external dev support to {feature_focus} post-raise."
    elif len(other_names) == 2:
        return f"I just wanted to reach out to see if {other_names[0]}, {other_names[1]}, and you have already considered bringing on external dev support to {feature_focus} post-raise."
    else:
        names_str = ", ".join(other_names)
        return f"I just wanted to reach out to see if {names_str}, and you have already considered bringing on external dev support to {feature_focus} post-raise."


def generate_ps_line(personal_signal: dict, article_url: str = "", recipient: dict = None) -> str:
    """
    Generate highly personalized PS line based on semantic summary.

    Format: Personal signal hook + celebration + location/conference invitation.
    """
    if recipient is None:
        recipient = {}

    location = recipient.get("location", "")

    # Build the celebration/location suffix
    if location:
        location_suffix = f"I hope you're celebrating this victory thoroughly. Maybe I'll catch you in {location} or at a conference in the US or Europe."
    else:
        location_suffix = "I hope you're celebrating this victory thoroughly. Maybe I'll catch you at a conference in the US or Europe."

    # Priority 1: Custom hook from research + location
    if personal_signal and personal_signal.get("hook_for_ps"):
        hook = personal_signal['hook_for_ps']
        return f"P.S. - {hook} {location_suffix}"

    # Priority 2: Generic with location
    return f"P.S. - {location_suffix}"


def generate_pps_line(location: str = "") -> str:
    """Generate PPS line with city mention if available."""
    if location and location.lower() not in ["unknown", "not found"]:
        return f"P.P.S. - Will you be in {location} or Europe at any point this year?"
    return "P.P.S. - Will you be in Europe at any point this year?"


def generate_email_body(
    company_info: dict,
    recipient: dict,
    all_decision_makers: list,
    language: str = "en"
) -> dict:
    """
    Generate the full email (subject + body) for a single recipient.

    Args:
        company_info: Dict with company, amount, round_type, article_url, etc.
        recipient: The person this email is for (enriched dict)
        all_decision_makers: All decision makers (for cross-reference)
        language: "en" or "es"

    Returns:
        Dict with subject, body, metadata
    """
    company = company_info.get("company", "Unknown")
    amount = company_info.get("amount", "")
    round_type = company_info.get("round_type", "")
    article_url = company_info.get("article_url", "")
    detected_region = company_info.get("detected_region", "US").upper()

    name = recipient.get("name", "there")
    role = recipient.get("role", "Founder")
    email = recipient.get("email", "")
    personal_signal = recipient.get("personal_signal", {})

    first_name = get_first_name(name)
    role_cat = get_role_category(role)
    team_estimate = get_team_estimate(amount)

    # Get other names (excluding recipient) for subject line (max 3 others + recipient = 4)
    other_names = get_cross_reference_names(all_decision_makers, name)

    # Generate subject line: up to 3 others + recipient last = max 4 names
    subject = generate_subject_line(company, amount, round_type, other_names, first_name)

    # Get feature focus from company info (researched from about page)
    feature_focus = company_info.get("feature_focus", "accelerate your roadmap")

    # Generate cross-reference line with feature focus
    cross_ref_line = generate_cross_reference_line(other_names, feature_focus)

    # Generate PS and PPS lines
    ps_line = generate_ps_line(personal_signal, article_url, recipient)
    location = recipient.get("location", "")
    pps_line = generate_pps_line(location)

    # Get founder pain quote with PROPER attribution
    pain_quote = get_founder_pain_quote()
    pain_quote_block = ""
    if pain_quote and pain_quote.get("quote"):
        founder = pain_quote.get("founder", "")
        company_name = pain_quote.get("company", "")
        source = pain_quote.get("source", "a recent podcast")

        # Build proper attribution
        if founder and company_name:
            attribution = f"{founder}, {company_name}"
        elif founder:
            attribution = founder
        elif company_name:
            attribution = f"A founder at {company_name}"
        else:
            attribution = "A founder"

        pain_quote_block = f'"{pain_quote["quote"]}" - {attribution} (shared this in {source})'

    # Standard value prop and CTA - UPDATED
    value_prop = "We provide pre-vetted Agile Tech Pods. Experienced devs, and I personally act as the PM. The pod will be ready to deploy in 72 hours. You see everything they build real-time, and I help you protect your focus."

    # CTA with company name
    cta = f"If you're currently hiring and you want somebody to also oversee the project delivery, just reply back. I can send you a Loom showing how it would look for {company}. If not, no worries at all. Maybe we can find a time at a future date."

    # Build email body based on role - ALL ROLES USE SIMILAR UPDATED STRUCTURE
    if role_cat == "CTO":
        body = f"""Hi {first_name},

Congrats on the {amount} raise, a new chapter for {company}.

{cross_ref_line}

{pain_quote_block}

After a raise, most CTOs I talk to are dealing with spending 10-24 hours/week on hiring instead of product, hard to verify if candidates are actually good, and needing senior talent but can't wait 6 months.

{value_prop}

{cta}

Jorge

{ps_line}

{pps_line}"""

    elif role_cat == "HR" or role_cat == "COO":
        body = f"""Hi {first_name},

Congrats on the {amount} raise, a new chapter for {company}.

{cross_ref_line}

{pain_quote_block}

Most People/Ops leads I talk to after a funding round are under pressure - leadership wants to move fast, but tech roles are taking 3-6 months to fill.

{value_prop}

{cta}

Jorge

{ps_line}

{pps_line}"""

    else:
        # CEO / Founder / Generic
        body = f"""Hi {first_name},

Congrats on the {amount} raise, a new chapter for {company}.

{cross_ref_line}

{pain_quote_block}

After a raise, most founders I talk to are dealing with pressure to ship fast, but hiring good engineers takes 3-6 months. Based on your raise size, you're probably looking at needing {team_estimate} to hit your next milestones.

{value_prop}

{cta}

Jorge

{ps_line}

{pps_line}"""

    return {
        "subject": subject,
        "body": body.strip(),
        "to_name": name,
        "to_role": role,
        "to_email": email,
        "to_linkedin": recipient.get("linkedin_url", ""),
        "to_twitter": recipient.get("twitter_url", ""),
        "to_instagram": recipient.get("instagram_url", ""),
        "to_facebook": recipient.get("facebook_url", ""),
        "personal_signal": personal_signal,
        "language": language,
        "cross_referenced": other_names
    }


def save_email_draft(
    email_data: dict,
    company_info: dict,
    save_to_file: bool = True
) -> str:
    """
    Save email draft to markdown file.

    Returns the markdown content.
    """
    company = company_info.get("company", "Unknown")
    name = email_data.get("to_name", "Unknown")
    role = email_data.get("to_role", "Executive")
    today = datetime.now().strftime("%Y-%m-%d")

    # Build markdown
    md = f"""# EMAIL DRAFT: {company} - {role}
**To:** {name} ({role})
**Generated:** {today}

---

## SUBJECT LINE
```
{email_data['subject']}
```

---

## EMAIL BODY

```
{email_data['body']}
```

---

## METADATA

| Field | Value |
|-------|-------|
| **To Email** | {email_data.get('to_email') or 'NEEDS LOOKUP'} |
| **LinkedIn** | {email_data.get('to_linkedin') or 'Not found'} |
| **Twitter** | {email_data.get('to_twitter') or 'Not found'} |
| **Instagram** | {email_data.get('to_instagram') or 'Not found'} |
| **Facebook** | {email_data.get('to_facebook') or 'Not found'} |
| **Cross-Referenced** | {', '.join(email_data.get('cross_referenced', [])) or 'None'} |

### Personal Signal Used
"""
    ps = email_data.get('personal_signal', {})
    if ps and ps.get('source'):
        md += f"""- **Source:** {ps.get('source', 'N/A')}
- **Summary:** {ps.get('summary', 'N/A')}
- **Hook:** {ps.get('hook_for_ps', 'N/A')}
"""
    else:
        md += "_No personal signal - used generic PS line_\n"

    md += """
---

_Generated by Jorge Email Generator_
"""

    # Save to file — each company gets its own folder with email_drafts/ subfolder
    if save_to_file:
        company_drafts_dir = DEEP_RESEARCH_DIR / company.replace(' ', '_') / "email_drafts"
        company_drafts_dir.mkdir(parents=True, exist_ok=True)
        safe_name = name.replace(" ", "_").replace(".", "")
        filename = f"{role}_{safe_name}_{today}.md"
        filepath = company_drafts_dir / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(md)

        print(f"      [OK] Email draft saved: {filepath}")

    return md


def generate_all_emails(
    company_info: dict,
    decision_makers: list,
    language: str = "en",
    save_to_file: bool = True
) -> list:
    """
    Generate email drafts for all decision makers.

    Args:
        company_info: Company data dict
        decision_makers: List of enriched person dicts
        language: "en" or "es"
        save_to_file: Whether to save markdown files

    Returns:
        List of email data dicts
    """
    emails = []

    for dm in decision_makers:
        name = dm.get("name", "")
        if not name or name.lower() in ["there", "unknown"]:
            continue

        email_data = generate_email_body(
            company_info=company_info,
            recipient=dm,
            all_decision_makers=decision_makers,
            language=language
        )

        if save_to_file:
            save_email_draft(email_data, company_info)

        emails.append(email_data)

    return emails


if __name__ == "__main__":
    # Test with sample data
    test_company = {
        "company": "Inferact",
        "amount": "$150M",
        "round_type": "Seed",
        "article_url": "https://techcrunch.com/example",
        "detected_region": "us"
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
                "summary": "Announced Inferact launch",
                "hook_for_ps": "Your post about 'making AI inference effortless' resonates - that's exactly what scaling teams should feel like."
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
        },
        {
            "name": "Sarah Chen",
            "role": "Head of People",
            "email": "sarah@inferact.ai",
            "linkedin_url": "",
            "twitter_url": "",
            "instagram_url": "",
            "facebook_url": "",
            "personal_signal": {}
        }
    ]

    emails = generate_all_emails(test_company, test_dms, save_to_file=False)

    print("\n" + "="*60)
    print("SAMPLE EMAIL (CEO):")
    print("="*60)
    print(f"SUBJECT: {emails[0]['subject']}")
    print("-"*60)
    print(emails[0]['body'])
