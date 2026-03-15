#!/usr/bin/env python3
"""
Extract ALL funding proposal drafts - with pagination to get everything.
"""

import json
import re
import base64
from pathlib import Path
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

PROJECT_ROOT = Path(__file__).parent.parent
token_file = PROJECT_ROOT / "token_gmail.json"

creds = Credentials.from_authorized_user_file(str(token_file))
service = build('gmail', 'v1', credentials=creds)

print("[INFO] Fetching ALL drafts (with pagination)...")

all_drafts = []
page_token = None

while True:
    if page_token:
        results = service.users().drafts().list(userId='me', maxResults=500, pageToken=page_token).execute()
    else:
        results = service.users().drafts().list(userId='me', maxResults=500).execute()

    drafts = results.get('drafts', [])
    all_drafts.extend(drafts)
    print(f"   Fetched {len(drafts)} drafts (total so far: {len(all_drafts)})")

    page_token = results.get('nextPageToken')
    if not page_token:
        break

print(f"\n[OK] Found {len(all_drafts)} TOTAL drafts")

funding_proposals = []

for i, draft in enumerate(all_drafts):
    draft_id = draft['id']
    draft_data = service.users().drafts().get(userId='me', id=draft_id, format='full').execute()
    message = draft_data.get('message', {})
    payload = message.get('payload', {})
    headers = payload.get('headers', [])

    subject = ""
    to = ""
    for h in headers:
        name = h['name'].lower()
        if name == 'subject':
            subject = h['value']
        elif name == 'to':
            to = h['value']

    # Only get [Funding Proposal] drafts
    if '[Funding Proposal]' not in subject:
        continue

    # Get full body
    body = ""
    if 'body' in payload and payload['body'].get('data'):
        body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8', errors='ignore')
    elif 'parts' in payload:
        for part in payload['parts']:
            if part.get('mimeType') == 'text/plain' and part.get('body', {}).get('data'):
                body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8', errors='ignore')
                break

    # Extract company info from body
    company_match = re.search(r'Company:\s*([^\n]+)', body)
    amount_match = re.search(r'Amount:\s*([^\n]+)', body)
    round_match = re.search(r'Round:\s*([^\n]+)', body)
    article_match = re.search(r'Article:\s*([^\n]+)', body)

    company = company_match.group(1).strip() if company_match else "UNKNOWN"
    amount = amount_match.group(1).strip() if amount_match else ""
    round_type = round_match.group(1).strip() if round_match else ""
    article = article_match.group(1).strip() if article_match else ""

    # Determine recency from article URL
    recency = "UNKNOWN"
    year_match = re.search(r'/(\d{4})/', article)
    if year_match:
        year = int(year_match.group(1))
        if year >= 2025:
            recency = "RECENT"
        elif year >= 2022:
            recency = f"OLD ({2026 - year} years)"
        else:
            recency = f"OLD ({2026 - year} years)"

    # Check for invalid URLs
    if any(x in article for x in ['/tag/', '/category/', '/subject/', '/list/', 'newsroom/subject']):
        recency = "INVALID URL"

    funding_proposals.append({
        "company": company,
        "amount": amount,
        "round": round_type,
        "article": article,
        "recency": recency,
        "subject": subject,
    })

    if (i + 1) % 20 == 0:
        print(f"   Processed {i + 1}/{len(all_drafts)} drafts... ({len(funding_proposals)} funding proposals found)")

print(f"\n[OK] Found {len(funding_proposals)} [Funding Proposal] drafts!")

# Sort: Recent first, then by company name
funding_proposals.sort(key=lambda x: (0 if x['recency'] == 'RECENT' else 1, x['company']))

# Save to JSON
output_json = PROJECT_ROOT / ".tmp" / "all_funding_proposals.json"
with open(output_json, 'w', encoding='utf-8') as f:
    json.dump(funding_proposals, f, indent=2, ensure_ascii=False)

# Create comprehensive markdown table
output_md = PROJECT_ROOT / ".tmp" / "all_funding_proposals.md"
with open(output_md, 'w', encoding='utf-8') as f:
    f.write("# ALL Funding Proposal Drafts\n")
    f.write(f"**Extracted:** {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    f.write(f"**Total [Funding Proposal] drafts:** {len(funding_proposals)}\n\n")

    # Summary
    recent = [c for c in funding_proposals if c['recency'] == 'RECENT']
    old = [c for c in funding_proposals if 'OLD' in c['recency']]
    invalid = [c for c in funding_proposals if c['recency'] == 'INVALID URL']
    unknown = [c for c in funding_proposals if c['recency'] == 'UNKNOWN']

    f.write("## Summary\n")
    f.write(f"- **Recent (2025-2026):** {len(recent)}\n")
    f.write(f"- **Old:** {len(old)}\n")
    f.write(f"- **Invalid URLs:** {len(invalid)}\n")
    f.write(f"- **Unknown date:** {len(unknown)}\n\n")

    f.write("---\n\n")
    f.write("## Complete List\n\n")
    f.write("| # | Company | Amount | Round | Recency | Article |\n")
    f.write("|---|---------|--------|-------|---------|--------|\n")

    for i, c in enumerate(funding_proposals, 1):
        article_short = c['article'][:60] + "..." if len(c['article']) > 60 else c['article']
        f.write(f"| {i} | {c['company']} | {c['amount']} | {c['round']} | {c['recency']} | [Link]({c['article']}) |\n")

print(f"\n[OK] Saved: {output_json}")
print(f"[OK] Saved: {output_md}")

# Print to console
print("\n" + "=" * 100)
print("ALL [FUNDING PROPOSAL] DRAFTS")
print("=" * 100)
for i, c in enumerate(funding_proposals, 1):
    print(f"{i:3}. {c['company']:20} | {c['amount']:12} | {c['round']:10} | {c['recency']:15} | {c['article'][:70]}")
print("=" * 100)
print(f"TOTAL: {len(funding_proposals)}")
