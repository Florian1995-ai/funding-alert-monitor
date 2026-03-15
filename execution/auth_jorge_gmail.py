#!/usr/bin/env python3
"""
Authorize Jorge's Gmail over a Zoom call.

Jorge only needs a browser - no Python required on his end.

Usage:
    python execution/auth_jorge_gmail.py
"""

from google_auth_oauthlib.flow import Flow
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# OAuth credentials file - download from Google Cloud Console
# See API_SETUP_GUIDE.md Section 5 for setup instructions
credentials_file = PROJECT_ROOT / "credentials.json"

if not credentials_file.exists():
    print("[ERROR] Gmail credentials not found")
    print(f"        Expected at: {credentials_file}")
    print()
    print("To fix this:")
    print("  1. Go to https://console.cloud.google.com")
    print("  2. Create a project and enable the Gmail API")
    print("  3. Go to APIs & Services > Credentials")
    print("  4. Create OAuth client ID (Desktop app)")
    print("  5. Download the JSON and rename it to 'credentials.json'")
    print(f"  6. Place it here: {PROJECT_ROOT}")
    print()
    print("See API_SETUP_GUIDE.md for detailed step-by-step instructions.")
    exit(1)

# Gmail API scopes - using most restrictive option for drafts
#
# gmail.compose = Create/edit/delete drafts + send
# gmail.send = Send only (no drafts)
# gmail.readonly = Read only (no write)
# mail.google.com = Full access (avoid!)
#
# Unfortunately Google doesn't offer "drafts only" without send.
# gmail.compose is the most restrictive scope that allows creating drafts.
#
# WHAT THIS CAN DO:
#   - Create drafts in Jorge's Gmail
#   - Edit/delete drafts
#   - Send emails (but our script only creates drafts)
#
# WHAT THIS CANNOT DO:
#   - Read Jorge's inbox
#   - Read Jorge's sent mail
#   - Access contacts
#   - Access any other Google services
#
# Use localhost redirect - Jorge will copy the code from the URL
REDIRECT_URI = 'http://localhost:8085'

flow = Flow.from_client_secrets_file(
    str(credentials_file),
    scopes=['https://www.googleapis.com/auth/gmail.compose'],
    redirect_uri=REDIRECT_URI
)

# Step 1: Generate URL
auth_url, _ = flow.authorization_url(prompt='consent', access_type='offline')

print("\n" + "="*60)
print("STEP 1: Send this URL to Jorge in Zoom chat")
print("="*60)
print(f"\n{auth_url}\n")

print("="*60)
print("STEP 2: Jorge opens the URL in his browser")
print("STEP 3: Jorge logs into his Gmail")
print("STEP 4: Jorge clicks 'Allow'")
print("STEP 5: Jorge's browser will show an ERROR PAGE - that's OK!")
print("STEP 6: Jorge copies the FULL URL from his browser address bar")
print("        (it will look like: http://localhost:8085/?code=4/0Axx...)")
print("STEP 7: Jorge pastes that URL to you in Zoom chat")
print("="*60)

# Step 2: Enter the URL Jorge gives you
url_from_jorge = input("\nPaste the URL from Jorge's address bar: ").strip()

if not url_from_jorge:
    print("[ERROR] No URL entered")
    exit(1)

# Extract the code from the URL
import urllib.parse
try:
    parsed = urllib.parse.urlparse(url_from_jorge)
    params = urllib.parse.parse_qs(parsed.query)
    code = params.get('code', [None])[0]

    if not code:
        print("[ERROR] Could not find 'code' in the URL")
        print("        Make sure Jorge copied the full URL from the address bar")
        exit(1)
except Exception as e:
    print(f"[ERROR] Failed to parse URL: {e}")
    exit(1)

# Step 3: Exchange code for token
try:
    flow.fetch_token(code=code)
    creds = flow.credentials
except Exception as e:
    print(f"[ERROR] Failed to exchange code: {e}")
    print("        The code may have expired. Ask Jorge to try again.")
    exit(1)

# Step 4: Save Jorge's token
token_path = PROJECT_ROOT / "token_jorge_gmail.json"
with open(token_path, 'w') as f:
    f.write(creds.to_json())

print("\n" + "="*60)
print("SUCCESS!")
print("="*60)
print(f"Jorge's Gmail is now authorized.")
print(f"Token saved to: {token_path}")
print("\nNext: Run the outreach script and drafts will appear in Jorge's Gmail.")
