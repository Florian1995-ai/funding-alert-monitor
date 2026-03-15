# API Setup Guide

This guide walks you through getting all the API keys needed to run the pipeline. Total setup time: ~15 minutes.

---

## 1. Tavily (Web Search)

**What it does:** Searches the web for funding news, hiring signals, and company info.
**Cost:** ~$0.005/query. Free tier: 1,000 searches/month.

### Steps
1. Go to [tavily.com](https://tavily.com)
2. Click "Get API Key" (sign up with Google or email)
3. On the dashboard, copy your API key (starts with `tvly-`)
4. Paste it in your `.env` file:
   ```
   TAVILY_API_KEY=tvly-your-key-here
   ```

---

## 2. Exa (LinkedIn & People Search)

**What it does:** Finds decision makers (CEO, CTO, HR) by searching LinkedIn profiles and company pages.
**Cost:** ~$0.01/query. Free tier: 1,000 searches/month.

### Steps
1. Go to [exa.ai](https://exa.ai)
2. Click "Get Started" and create an account
3. Go to Dashboard > API Keys
4. Create a new key and copy it (starts with `exa-`)
5. Paste it in your `.env` file:
   ```
   EXA_API_KEY=exa-your-key-here
   ```

---

## 3. Perplexity (Deep Research & Enrichment)

**What it does:** Finds email addresses, locations, personal signals, and resolves LinkedIn handles to real names. Uses the Sonar model with real-time web search.
**Cost:** ~$0.005/query. Free tier available.

### Steps
1. Go to [perplexity.ai](https://perplexity.ai)
2. Click your profile icon > Settings > API
3. Or go directly to [perplexity.ai/settings/api](https://www.perplexity.ai/settings/api)
4. Generate an API key (starts with `pplx-`)
5. Paste it in your `.env` file:
   ```
   PERPLEXITY_API_KEY=pplx-your-key-here
   ```

---

## 4. OpenAI (Email Generation)

**What it does:** Currently used as a fallback for email generation. The pipeline mostly uses templates, so this key is optional but recommended.
**Cost:** ~$0.01/email.

### Steps
1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign in or create an account
3. Go to API Keys (left sidebar) > Create new secret key
4. Copy the key (starts with `sk-`)
5. Paste it in your `.env` file:
   ```
   OPENAI_API_KEY=sk-your-key-here
   ```

---

## 5. Gmail OAuth (Email Drafts)

**What it does:** Creates email drafts directly in your Gmail account so you can review and send.
**Cost:** Free.

### Steps

#### A. Create Google Cloud credentials (one-time)
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g., "Jorge Outreach")
3. Enable the **Gmail API**:
   - Go to APIs & Services > Library
   - Search "Gmail API" > Enable
4. Create OAuth credentials:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth client ID"
   - Application type: "Desktop app"
   - Download the JSON file
5. Rename it to `credentials.json` and place it in this folder

#### B. Authorize your Gmail
```bash
python execution/auth_jorge_gmail.py
```
This opens a browser window. Sign in with your Gmail and grant permissions for:
- **Gmail compose** (to create drafts)
- **Gmail readonly** (to check existing drafts)

This creates `token_gmail.json` — keep this file safe, never share it.

---

## Quick Verification

After setting up all keys, test the pipeline with a dry run:

```bash
python execution/jorge_mvp_orchestrator.py --company "TestCompany" --amount "$10M" --round "Seed" --dry-run
```

If you see decision makers being found and email drafts being generated (without Gmail), all keys are working.

---

## Monthly Cost Estimate

| Service | Per Company | 30 Companies/Month |
|---------|-----------|-------------------|
| Tavily | ~$0.05 | ~$1.50 |
| Exa | ~$0.10 | ~$3.00 |
| Perplexity | ~$0.02 | ~$0.60 |
| OpenAI | ~$0.03 | ~$0.90 |
| **Total** | **~$0.20** | **~$6/month** |

RSS monitoring (16 feeds) is free.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `TAVILY_API_KEY not found` | Check your `.env` file has no spaces around `=` |
| `EXA_API_KEY not found` | Make sure the key starts with `exa-` |
| `Gmail token not found` | Run `python execution/auth_jorge_gmail.py` |
| `Token expired` | Delete `token_gmail.json` and re-run auth script |
| Names show as handles (e.g., "Johndoe") | Perplexity key needed for name resolution |
| No location in emails | Perplexity key needed for city lookup |
