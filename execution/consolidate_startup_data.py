#!/usr/bin/env python3
"""
Consolidate all recently funded startup data from multiple research sources
into a unified master CSV and enriched JSON for Jorge's delivery.

Sources:
1. Perplexity research (CSV embedded in markdown)
2. VapiCon voice AI research (CSV embedded in markdown)
3. Claude 75+ companies (markdown tables + structured sections)
4. Gmail draft tracking (deduplication reference)
5. Existing research reports (.tmp/research_reports/)
"""

import csv
import json
import re
import io
import sys
from pathlib import Path

# Fix Windows cp1252 encoding errors when printing Unicode characters
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
RESOURCES_DIR = PROJECT_ROOT / "Resources" / "Recentlyfundeddeepresearch"
TMP_DIR = PROJECT_ROOT / ".tmp"
DELIVERY_DIR = PROJECT_ROOT / "delivery" / "data"


def parse_perplexity_csv(filepath: Path) -> list:
    """Parse the Perplexity research file which has embedded CSV data."""
    companies = []
    content = filepath.read_text(encoding="utf-8")

    # Find the CSV section - starts with "company_name,company_website,"
    csv_start = content.find("company_name,company_website,")
    if csv_start == -1:
        print("[WARN] No CSV section found in Perplexity file")
        return companies

    # Extract CSV lines until we hit a non-CSV line (JSON section or blank)
    csv_text = content[csv_start:]
    lines = csv_text.split("\n")
    csv_lines = [lines[0]]  # header
    for line in lines[1:]:
        if not line.strip() or line.startswith("2)") or line.startswith("json") or line.startswith("["):
            break
        csv_lines.append(line)

    reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
    for row in reader:
        amount_raw = row.get("funding_amount", "0")
        try:
            amount = int(str(amount_raw).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            amount = 0

        companies.append({
            "company_name": row.get("company_name", "").strip(),
            "website": row.get("company_website", "").strip(),
            "hq_location": row.get("hq_location", "").strip(),
            "industry": row.get("industry", "").strip(),
            "product_category": row.get("product_category", "").strip(),
            "funding_round": row.get("funding_round", "").strip(),
            "funding_amount": amount,
            "funding_date": row.get("funding_date", "").strip(),
            "lead_investor": row.get("funding_investors_lead", "").strip().strip('"'),
            "other_investors": row.get("funding_investors_others", "").strip().strip('"'),
            "hiring_signal": row.get("hiring_signal_text", "").strip().strip('"'),
            "careers_page": row.get("careers_page_url", "").strip().strip('"'),
            "ceo_name": row.get("founder_ceo_name", "").strip().strip('"'),
            "ceo_linkedin": row.get("founder_ceo_linkedin", "").strip().strip('"'),
            "source_url": row.get("funding_source_url", "").strip().strip('"'),
            "data_source": "perplexity",
            "notes": (row.get("notes") or "").strip().strip('"'),
        })

    print(f"  [OK] Parsed {len(companies)} companies from Perplexity CSV")
    return companies


def parse_vapicon_csv(filepath: Path) -> list:
    """Parse VapiCon voice AI research file with embedded CSV."""
    companies = []
    content = filepath.read_text(encoding="utf-8")

    # Find CSV starting with "Company,Domain,Industry,Website,"
    csv_start = content.find("Company,Domain,Industry,Website,")
    if csv_start == -1:
        print("[WARN] No CSV section found in VapiCon file")
        return companies

    csv_text = content[csv_start:]
    lines = csv_text.split("\n")
    csv_lines = [lines[0]]
    for line in lines[1:]:
        if not line.strip() or line.startswith("🎯") or line.startswith("Copy{"):
            break
        csv_lines.append(line)

    reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
    for row in reader:
        amount_raw = row.get("Recent_Funding_Amount", "0")
        try:
            amount = int(str(amount_raw).replace(",", "").replace("$", ""))
        except (ValueError, TypeError):
            amount = 0

        companies.append({
            "company_name": row.get("Company", "").strip(),
            "website": row.get("Website", "").strip(),
            "hq_location": "",
            "industry": row.get("Domain", "").strip() + " / " + row.get("Industry", "").strip(),
            "product_category": row.get("Voice_AI_Technology", "").strip().strip('"'),
            "funding_round": row.get("Funding_Round", "").strip(),
            "funding_amount": amount,
            "funding_date": row.get("Funding_Date", "").strip(),
            "lead_investor": row.get("Valuation_Lead_Investor", "").strip().strip('"'),
            "other_investors": row.get("Other_Investors", "").strip().strip('"'),
            "hiring_signal": row.get("Hiring_Signal", "").strip().strip('"'),
            "careers_page": row.get("Careers_Page_URL", "").strip().strip('"'),
            "ceo_name": row.get("CEO_Founder", "").strip().strip('"'),
            "ceo_linkedin": row.get("CEO_LinkIn", "").strip().strip('"'),
            "source_url": row.get("Press_Release_Link", "").strip().strip('"'),
            "data_source": "vapicon_research",
            "notes": row.get("Company_Description", "").strip().strip('"'),
        })

    print(f"  [OK] Parsed {len(companies)} companies from VapiCon CSV")
    return companies


def parse_claude_markdown(filepath: Path) -> list:
    """Parse Claude's 75+ companies from structured markdown sections and tables."""
    companies = []
    content = filepath.read_text(encoding="utf-8")

    # Parse Tier 1 detailed sections (### Company Name format)
    tier1_pattern = re.compile(
        r'###\s+(.+?)\n'
        r'\*\*(.+?)\*\*\s*\|\s*(.+?)\s*\n'
        r'\*\*(\$[\d,.]+[MBK]?(?:\+)?)\s*(?:.*?)\*\*\s*\|\s*(\w+\s+\d{4})\s*\|\s*(.+?)\s*\n'
        r'(.+?)(?=\n---|\n###|\n##|\Z)',
        re.DOTALL
    )

    for match in tier1_pattern.finditer(content):
        name = match.group(1).strip()
        location = match.group(2).strip()
        website_or_domain = match.group(3).strip()
        amount_str = match.group(4).strip()
        date_info = match.group(5).strip()
        lead_investor = match.group(6).strip()
        body = match.group(7).strip()

        # Parse amount
        amount = parse_amount(amount_str)

        # Parse round from the line (look for "Series X" or "Seed" in the full line)
        round_match = re.search(r'(Series\s+[A-Z]\+?|Seed|Pre-Seed|Growth|Conv\.\s*Note)', match.group(0))
        funding_round = round_match.group(1) if round_match else ""

        # Extract hiring signal from body
        hiring_match = re.search(r'\*\*Hiring Signals?:\*\*\s*(.+?)(?:\n|$)', body)
        hiring_signal = hiring_match.group(1).strip() if hiring_match else ""

        # Extract CEO/founder name
        founder_match = re.search(r'(?:CEO|Founder|Co-founder)s?\s+(\w+\s+\w+(?:\s+\w+)?)', body)
        ceo_name = founder_match.group(1).strip() if founder_match else ""

        website = website_or_domain if website_or_domain.startswith("http") else f"https://{website_or_domain}" if "." in website_or_domain else ""

        companies.append({
            "company_name": name,
            "website": website,
            "hq_location": location,
            "industry": "",
            "product_category": "",
            "funding_round": funding_round,
            "funding_amount": amount,
            "funding_date": date_info,
            "lead_investor": lead_investor,
            "other_investors": "",
            "hiring_signal": hiring_signal[:300] if hiring_signal else "",
            "careers_page": "",
            "ceo_name": ceo_name,
            "ceo_linkedin": "",
            "source_url": "",
            "data_source": "claude_research",
            "notes": "",
        })

    # Parse markdown tables (| Company | Location | Funding | ...)
    table_pattern = re.compile(
        r'\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*(\$?[\d,.]+[MBK]?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]*?)\s*\|'
    )

    for match in table_pattern.finditer(content):
        name = match.group(1).strip()
        location = match.group(2).strip()
        amount_str = match.group(3).strip()
        funding_round = match.group(4).strip()
        date_info = match.group(5).strip()
        lead_investor = match.group(6).strip()
        hiring_signal = match.group(7).strip()

        # Skip header rows and separator rows
        if name.lower() in ["company", "------", "---"] or "---" in name:
            continue

        amount = parse_amount(amount_str)
        if amount == 0:
            continue

        # Check if this company already exists (from tier 1)
        existing = [c for c in companies if c["company_name"].lower() == name.lower()]
        if existing:
            continue

        companies.append({
            "company_name": name,
            "website": "",
            "hq_location": location,
            "industry": "",
            "product_category": "",
            "funding_round": funding_round,
            "funding_amount": amount,
            "funding_date": date_info,
            "lead_investor": lead_investor,
            "other_investors": "",
            "hiring_signal": hiring_signal[:300],
            "careers_page": "",
            "ceo_name": "",
            "ceo_linkedin": "",
            "source_url": "",
            "data_source": "claude_research",
            "notes": "",
        })

    print(f"  [OK] Parsed {len(companies)} companies from Claude markdown")
    return companies


def parse_genspark_numbered_list(filepath: Path) -> list:
    """Parse GenSpark files that have numbered company lists like:
    1. Modular - $220M Series B - San Jose, CA
    or structured sections with ### Company Name headings.
    """
    companies = []
    content = filepath.read_text(encoding="utf-8")

    # Pattern 1: Numbered list "N. Company - $XXM Round - Location"
    numbered = re.compile(
        r'^\s*\d+\.\s+(.+?)\s*[-–]\s*\$?([\d,.]+[MBK]?)\s*(Series\s+[A-Z]\+?|Seed|Pre-Seed|Growth|Strategic)?\s*[-–]\s*(.+?)$',
        re.MULTILINE
    )
    for m in numbered.finditer(content):
        name = m.group(1).strip().rstrip(" -–")
        amount = parse_amount("$" + m.group(2).strip())
        funding_round = m.group(3).strip() if m.group(3) else ""
        location = m.group(4).strip()

        if amount > 0 and name:
            companies.append({
                "company_name": name,
                "website": "",
                "hq_location": location,
                "industry": "",
                "product_category": "",
                "funding_round": funding_round,
                "funding_amount": amount,
                "funding_date": "",
                "lead_investor": "",
                "other_investors": "",
                "hiring_signal": "",
                "careers_page": "",
                "ceo_name": "",
                "ceo_linkedin": "",
                "source_url": "",
                "data_source": "genspark",
                "notes": "",
            })

    # Pattern 2: Simple bullet list "- **Company** - $XXM Round"
    bullet = re.compile(
        r'[-*]\s+\*?\*?(.+?)\*?\*?\s*[-–]\s*\$?([\d,.]+[MBK]?)\s*(Series\s+[A-Z]\+?|Seed|Pre-Seed|Growth)?',
        re.MULTILINE
    )

    # Also try the GenSpark embedded CSV if present
    if "Company,Domain," in content or "company_name," in content:
        # Already handled by other parsers, skip
        pass
    else:
        for m in bullet.finditer(content):
            name = m.group(1).strip().rstrip(" -–*")
            if not name or len(name) > 80:
                continue
            amount = parse_amount("$" + m.group(2).strip())
            funding_round = m.group(3).strip() if m.group(3) else ""
            if amount > 0:
                existing = [c for c in companies if c["company_name"].lower() == name.lower()]
                if not existing:
                    companies.append({
                        "company_name": name,
                        "website": "",
                        "hq_location": "",
                        "industry": "",
                        "product_category": "",
                        "funding_round": funding_round,
                        "funding_amount": amount,
                        "funding_date": "",
                        "lead_investor": "",
                        "other_investors": "",
                        "hiring_signal": "",
                        "careers_page": "",
                        "ceo_name": "",
                        "ceo_linkedin": "",
                        "source_url": "",
                        "data_source": "genspark",
                        "notes": "",
                    })

    # Extract CEO/founder names from structured sections
    founder_pattern = re.compile(
        r'(?:CEO|Founder|Co-founder)[:\s]+(.+?)(?:\s*[-–(]|\s*\n)',
        re.IGNORECASE
    )
    hiring_pattern = re.compile(
        r'(?:Hiring\s*Signals?|HIRING)[:\s]+(.+?)(?:\n|$)',
        re.IGNORECASE
    )

    # Try to enrich companies found above with nearby text (limited window)
    for c in companies:
        name = c["company_name"]
        # Find the company mention and grab only the next ~500 chars (not the whole document)
        name_pos = content.lower().find(name.lower())
        if name_pos == -1:
            continue
        # Take a small window after the company name (500 chars max)
        window = content[name_pos:name_pos + 500]
        # Stop at section boundaries
        for boundary in ["\n---", "\n###", "\n##", "\n\n\n"]:
            idx = window.find(boundary, len(name))
            if idx > 0:
                window = window[:idx]
                break

        fm = founder_pattern.search(window)
        if fm and not c["ceo_name"]:
            c["ceo_name"] = fm.group(1).strip()[:60]
        hm = hiring_pattern.search(window)
        if hm and not c["hiring_signal"]:
            c["hiring_signal"] = hm.group(1).strip()[:300]

    if companies:
        print(f"  [OK] Parsed {len(companies)} companies from GenSpark file: {filepath.name}")
    return companies


def parse_genspark_csv(filepath: Path) -> list:
    """Parse GenSpark files that contain embedded CSV data with different headers."""
    companies = []
    content = filepath.read_text(encoding="utf-8")

    # Look for CSV sections with various header patterns
    csv_headers = [
        "Company,Domain,Industry,Website,",
        "company_name,company_website,",
        "Company,Funding,Amount,",
    ]

    for header in csv_headers:
        csv_start = content.find(header)
        if csv_start != -1:
            csv_text = content[csv_start:]
            lines = csv_text.split("\n")
            csv_lines = [lines[0]]
            for line in lines[1:]:
                stripped = line.strip()
                if not stripped or stripped.startswith("🎯") or stripped.startswith("Copy{") or stripped.startswith("{") or stripped.startswith("[") or stripped.startswith("##"):
                    break
                csv_lines.append(line)

            if len(csv_lines) > 1:
                try:
                    reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
                    for row in reader:
                        name = (row.get("Company") or row.get("company_name") or "").strip()
                        if not name:
                            continue

                        amount_raw = (row.get("Recent_Funding_Amount") or row.get("funding_amount") or row.get("Amount") or "0")
                        try:
                            amount = int(str(amount_raw).replace(",", "").replace("$", ""))
                        except (ValueError, TypeError):
                            amount = 0

                        companies.append({
                            "company_name": name,
                            "website": (row.get("Website") or row.get("company_website") or "").strip(),
                            "hq_location": (row.get("hq_location") or "").strip(),
                            "industry": (row.get("Domain") or row.get("industry") or "").strip(),
                            "product_category": (row.get("Voice_AI_Technology") or row.get("product_category") or "").strip().strip('"'),
                            "funding_round": (row.get("Funding_Round") or row.get("funding_round") or "").strip(),
                            "funding_amount": amount,
                            "funding_date": (row.get("Funding_Date") or row.get("funding_date") or "").strip(),
                            "lead_investor": (row.get("Valuation_Lead_Investor") or row.get("funding_investors_lead") or "").strip().strip('"'),
                            "other_investors": (row.get("Other_Investors") or row.get("funding_investors_others") or "").strip().strip('"'),
                            "hiring_signal": (row.get("Hiring_Signal") or row.get("hiring_signal_text") or "").strip().strip('"'),
                            "careers_page": (row.get("Careers_Page_URL") or row.get("careers_page_url") or "").strip().strip('"'),
                            "ceo_name": (row.get("CEO_Founder") or row.get("founder_ceo_name") or "").strip().strip('"'),
                            "ceo_linkedin": (row.get("CEO_LinkIn") or row.get("founder_ceo_linkedin") or "").strip().strip('"'),
                            "source_url": (row.get("Press_Release_Link") or row.get("funding_source_url") or "").strip().strip('"'),
                            "data_source": "genspark",
                            "notes": (row.get("Company_Description") or row.get("notes") or "").strip().strip('"'),
                        })
                except Exception as e:
                    print(f"  [WARN] CSV parse error in {filepath.name}: {e}")

    if companies:
        print(f"  [OK] Parsed {len(companies)} companies from GenSpark CSV: {filepath.name}")
    return companies


def parse_amount(amount_str: str) -> int:
    """Parse funding amount string to integer (USD)."""
    if not amount_str:
        return 0
    cleaned = amount_str.replace("$", "").replace(",", "").replace("+", "").strip()
    try:
        if cleaned.upper().endswith("B"):
            return int(float(cleaned[:-1]) * 1_000_000_000)
        elif cleaned.upper().endswith("M"):
            return int(float(cleaned[:-1]) * 1_000_000)
        elif cleaned.upper().endswith("K"):
            return int(float(cleaned[:-1]) * 1_000)
        else:
            return int(float(cleaned))
    except (ValueError, TypeError):
        return 0


def format_amount(amount: int) -> str:
    """Format integer amount to human-readable string."""
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.1f}B"
    elif amount >= 1_000_000:
        return f"${amount / 1_000_000:.0f}M"
    elif amount >= 1_000:
        return f"${amount / 1_000:.0f}K"
    elif amount > 0:
        return f"${amount}"
    return ""


def load_gmail_draft_companies() -> set:
    """Load company names from Gmail draft tracking to mark duplicates."""
    drafted = set()
    proposals_file = TMP_DIR / "all_funding_proposals.json"
    if proposals_file.exists():
        try:
            data = json.loads(proposals_file.read_text(encoding="utf-8"))
            for entry in data:
                name = entry.get("company", "").strip().lower()
                if name:
                    drafted.add(name)
        except Exception:
            pass

    # Also check the markdown version
    proposals_md = TMP_DIR / "all_funding_proposals.md"
    if proposals_md.exists():
        content = proposals_md.read_text(encoding="utf-8")
        for match in re.finditer(r'\|\s*\d+\s*\|\s*([^|]+?)\s*\|', content):
            name = match.group(1).strip().lower()
            if name and name not in ["company", "---"]:
                drafted.add(name)

    print(f"  [OK] Loaded {len(drafted)} companies from Gmail drafts (dedup reference)")
    return drafted


def load_research_reports() -> dict:
    """Load existing research reports and their content."""
    reports = {}
    reports_dir = TMP_DIR / "research_reports"
    if reports_dir.exists():
        for f in reports_dir.glob("*.md"):
            # Extract company name from filename: "ElevenLabs_research_2026-02-05.md"
            name = f.stem.split("_research_")[0]
            reports[name.lower()] = f.read_text(encoding="utf-8")
    print(f"  [OK] Loaded {len(reports)} existing research reports")
    return reports


def is_valid_company_name(name: str) -> bool:
    """Filter out garbage parsed as company names."""
    if not name or len(name) > 60:
        return False
    # Must not contain newlines, brackets, or meta-text patterns
    bad_patterns = ["\n", "\r", "[", "]", "companies #", "average ", "hiring volume",
                    "technical and", "company profiles", "complete founder", "stanford phd",
                    "###", "option ", "tier ", "view full", "extract minimum",
                    "extract at least", "extract complete", "verify every"]
    for bp in bad_patterns:
        if bp in name.lower():
            return False
    # Must start with a letter or digit
    if not name[0].isalnum():
        return False
    # Reject names that start with location patterns (City, ST - ...)
    if re.match(r'^[A-Z]{2,3},\s*[A-Z]{2}\s*-', name):
        return False
    # Reject names starting with full location like "London", "Boston, MA -"
    if re.match(r'^(?:London|Boston|NYC|Mountain View|Palo Alto|Berkeley|Austin|San Jose|Bristol)[^a-z]', name):
        return False
    # Reject names that are mostly markdown formatting
    if name.startswith("1. **") or name.startswith("**"):
        return False
    # Reject pure year strings or very short non-company strings
    if re.match(r'^20\d{2}$', name.strip()):
        return False
    if len(name.strip()) <= 2:
        return False
    # Reject names with "- " prefix followed by company (indicates prior line's data leaked in)
    if " - " in name and re.match(r'^.+,\s*[A-Z]{2}\s*-', name):
        return False
    return True


def clean_company_name(name: str) -> str:
    """Clean up a company name by removing common artifacts."""
    if not name:
        return name
    # Strip markdown bold markers
    name = name.strip("*").strip()
    # Strip leading "N. " numbered list prefix
    name = re.sub(r'^\d+\.\s+\*?\*?', '', name).strip("*").strip()
    # Strip trailing parenthetical if it's just a category hint, keep if it's part of the name
    # e.g. "Modular (AI Infrastructure)" -> "Modular" but "Character.AI" stays
    cleaned = re.sub(r'\s*\((?:AI |Voice |Legal |Health|Content |Document |Conversational |ML |AutoML |IT |Data |Computer |Presentations )[\w\s/]+\)$', '', name)
    return cleaned.strip()


def deduplicate(companies: list) -> list:
    """Remove duplicate companies, keeping the entry with most data."""
    seen = {}
    for c in companies:
        # Clean the company name first
        c["company_name"] = clean_company_name(c["company_name"])
        if not c["company_name"] or not is_valid_company_name(c["company_name"]):
            continue
        key = c["company_name"].lower().strip()
        if key in seen:
            # Keep the one with more data
            existing = seen[key]
            existing_score = sum(1 for v in existing.values() if v)
            new_score = sum(1 for v in c.values() if v)
            if new_score > existing_score:
                seen[key] = c
        else:
            seen[key] = c
    return list(seen.values())


def is_recent(date_str: str) -> bool:
    """Check if a funding date is recent (2024+)."""
    if not date_str:
        return True  # Assume recent if unknown

    # Look for year patterns
    year_match = re.search(r'20(\d{2})', date_str)
    if year_match:
        year = int("20" + year_match.group(1))
        return year >= 2024
    return True


def main():
    print("=" * 70)
    print("CONSOLIDATING STARTUP DATA FOR JORGE'S DELIVERY")
    print("=" * 70)

    all_companies = []

    # Source 1: Perplexity research files
    print("\n[1/5] Parsing Perplexity research files...")
    for pf in RESOURCES_DIR.glob("perplexity*recentlyfundedstartups*.md"):
        all_companies.extend(parse_perplexity_csv(pf))

    # Source 2: VapiCon voice AI research (original file has embedded CSV)
    print("\n[2/5] Parsing VapiCon voice AI research...")
    vapicon_file = RESOURCES_DIR / "recentlyfundedstartups.md"
    if vapicon_file.exists():
        all_companies.extend(parse_vapicon_csv(vapicon_file))

    # Source 3: Claude 75+ companies
    print("\n[3/5] Parsing Claude research files...")
    for cf in RESOURCES_DIR.glob("claude*fundedstartups*.md"):
        all_companies.extend(parse_claude_markdown(cf))

    # Source 4: ALL GenSpark Kopie files (various formats)
    print("\n[4/5] Parsing all GenSpark research files (Kopie files)...")
    for gf in sorted(RESOURCES_DIR.glob("*Kopie*.md")):
        # Try CSV parse first, then numbered list parse
        csv_results = parse_genspark_csv(gf)
        if csv_results:
            all_companies.extend(csv_results)
        else:
            list_results = parse_genspark_numbered_list(gf)
            if list_results:
                all_companies.extend(list_results)
            else:
                print(f"  [SKIP] No structured data found in: {gf.name}")

    # Source 5: Gmail draft tracking (dedup reference)
    print("\n[5/5] Loading Gmail draft tracking for deduplication...")
    drafted_companies = load_gmail_draft_companies()
    research_reports = load_research_reports()

    # Deduplicate
    print(f"\n--- Raw total: {len(all_companies)} entries ---")
    companies = deduplicate(all_companies)
    print(f"--- After dedup: {len(companies)} unique companies ---")

    # Filter out old companies
    recent = [c for c in companies if is_recent(c.get("funding_date", ""))]
    print(f"--- After filtering old: {len(recent)} recent companies ---")

    # Score and sort by hiring signal strength (as GenSpark did), then funding amount
    def hiring_score(c):
        """Score hiring signal strength: higher = stronger signal."""
        signal = (c.get("hiring_signal", "") or "").lower()
        score = 0
        if signal:
            score += 1  # Has any signal at all
            # Strong keywords
            for kw in ["hiring", "we're hiring", "open positions", "actively hiring",
                        "expand", "scaling", "doubling", "triple", "grow"]:
                if kw in signal:
                    score += 2
            # Quantified signals are strongest
            if re.search(r'\d+\+?\s*(?:open|positions|roles|jobs|employees)', signal):
                score += 3
            # Explicit founder quotes about hiring
            if "headcount" in signal or "team expansion" in signal:
                score += 2
        return score

    recent.sort(key=lambda x: (hiring_score(x), x.get("funding_amount", 0)), reverse=True)

    # Enrich with draft/research status
    for c in recent:
        name_lower = c["company_name"].lower()
        c["has_email_draft"] = name_lower in drafted_companies
        c["has_deep_research"] = name_lower in research_reports
        c["funding_amount_display"] = format_amount(c.get("funding_amount", 0))

    # Create output directory
    DELIVERY_DIR.mkdir(parents=True, exist_ok=True)

    # Write master CSV
    csv_path = DELIVERY_DIR / "master_startups.csv"
    csv_fields = [
        "company_name", "website", "hq_location", "industry", "product_category",
        "funding_round", "funding_amount_display", "funding_amount", "funding_date",
        "lead_investor", "other_investors", "hiring_signal", "careers_page",
        "ceo_name", "ceo_linkedin", "source_url",
        "has_deep_research", "has_email_draft", "data_source", "notes"
    ]

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        writer.writeheader()
        for c in recent:
            writer.writerow(c)

    print(f"\n[OK] Master CSV: {csv_path} ({len(recent)} companies)")

    # Write enriched JSON
    json_entries = []
    for c in recent:
        name_lower = c["company_name"].lower()
        entry = {
            "company": {
                "name": c["company_name"],
                "website": c.get("website", ""),
                "hq_location": c.get("hq_location", ""),
                "industry": c.get("industry", ""),
                "product_category": c.get("product_category", ""),
            },
            "funding": {
                "round": c.get("funding_round", ""),
                "amount_usd": c.get("funding_amount", 0),
                "amount_display": c.get("funding_amount_display", ""),
                "date": c.get("funding_date", ""),
                "lead_investor": c.get("lead_investor", ""),
                "other_investors": c.get("other_investors", ""),
                "source_url": c.get("source_url", ""),
            },
            "leadership": {
                "ceo_name": c.get("ceo_name", ""),
                "ceo_linkedin": c.get("ceo_linkedin", ""),
            },
            "hiring": {
                "signal": c.get("hiring_signal", ""),
                "careers_page": c.get("careers_page", ""),
            },
            "status": {
                "has_deep_research": c.get("has_deep_research", False),
                "has_email_draft": c.get("has_email_draft", False),
                "data_source": c.get("data_source", ""),
            },
            "notes": c.get("notes", ""),
        }

        # Embed research report if available
        if name_lower in research_reports:
            entry["research_report_markdown"] = research_reports[name_lower]

        json_entries.append(entry)

    json_path = DELIVERY_DIR / "master_startups_enriched.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(json_entries, f, indent=2, ensure_ascii=False)

    print(f"[OK] Enriched JSON: {json_path} ({len(json_entries)} entries)")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total unique recent companies: {len(recent)}")
    print(f"With deep research reports:     {sum(1 for c in recent if c.get('has_deep_research'))}")
    print(f"With existing email drafts:     {sum(1 for c in recent if c.get('has_email_draft'))}")
    print(f"\nBy data source:")
    sources = {}
    for c in recent:
        src = c.get("data_source", "unknown")
        sources[src] = sources.get(src, 0) + 1
    for src, count in sorted(sources.items(), key=lambda x: -x[1]):
        print(f"  {src}: {count}")

    print(f"\nTop 30 (sorted by hiring signal strength, then funding):")
    for i, c in enumerate(recent[:30], 1):
        amount = c.get("funding_amount_display", "?")
        hs = hiring_score(c)
        hs_label = f"[HS:{hs}]" if hs > 0 else "[no HS]"
        research = " [RESEARCH]" if c.get("has_deep_research") else ""
        draft = " [DRAFTED]" if c.get("has_email_draft") else ""
        print(f"  {i:2d}. {c['company_name']:<30s} {amount:>10s}  {c.get('funding_round', ''):<12s} {hs_label}{research}{draft}")

    print(f"\nFiles written to: {DELIVERY_DIR}")


if __name__ == "__main__":
    main()
