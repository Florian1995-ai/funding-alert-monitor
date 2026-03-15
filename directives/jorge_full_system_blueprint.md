# Jorge Funding Outreach System - Complete Blueprint

> This document defines the complete automation system for generating founder-resonant outreach emails to recently funded startups.

---

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         JORGE FUNDING OUTREACH SYSTEM                       │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────┐    ┌───────────────┐    ┌───────────────────────────┐   │
│  │   TRIGGERS    │───▶│   RESEARCH    │───▶│      ENRICHMENT           │   │
│  │               │    │               │    │                           │   │
│  │ • RSS Feeds   │    │ • Company     │    │ • Decision Makers         │   │
│  │ • Tavily      │    │ • Founder     │    │ • LinkedIn Profiles       │   │
│  │ • Manual      │    │ • Hiring      │    │ • Contact Info            │   │
│  └───────────────┘    └───────────────┘    └───────────────────────────┘   │
│          │                    │                         │                   │
│          ▼                    ▼                         ▼                   │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    FOUNDER PAIN KNOWLEDGE BASE                        │ │
│  │  • YouTube transcripts from founder interviews                        │ │
│  │  • Exact phrases, emotional signals, pain points                      │ │
│  │  • Queryable by: industry, stage, region, role                        │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                       EMAIL GENERATION                                │ │
│  │  • Role-specific angles (CEO vs CTO vs HR)                            │ │
│  │  • Language-aware (Spanish for Spain/LATAM, English for EU/US)        │ │
│  │  • Pain-resonant language from knowledge base                         │ │
│  │  • Personalization: funding amount, team size, hiring signals         │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                    │                                        │
│                                    ▼                                        │
│  ┌───────────────────────────────────────────────────────────────────────┐ │
│  │                    GMAIL DRAFTS (Never Auto-Send)                     │ │
│  │  • One draft per decision maker                                       │ │
│  │  • Jorge reviews and sends manually                                   │ │
│  │  • Tracking: open rates, reply rates, meetings booked                 │ │
│  └───────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Geographic Priority

| Priority | Region | Language | Notes |
|----------|--------|----------|-------|
| 1 | Spain | Spanish | Jorge's home market, highest conversion |
| 2 | Europe | English | Germany, France, UK, Netherlands, Sweden, Ireland, Portugal, Italy |
| 3 | USA | English | Largest market, more competition |

---

## Industry Focus

**Primary:**
- AI / Machine Learning companies
- Technical infrastructure
- Developer tools
- SaaS platforms

**Secondary:**
- Fintech
- Blockchain
- Robotics
- Clean energy / Climate tech

---

## Data Points Taxonomy

### 1. COMPANY-LEVEL DATA

| Data Point | Source | Priority | Use Case |
|------------|--------|----------|----------|
| Company name | RSS/Tavily | Required | Personalization |
| Funding round | Press release | Required | Messaging angle |
| Amount raised | Press release | Required | Team size estimate |
| Location/HQ | Enrichment | Required | Geographic filtering |
| Industry/vertical | Enrichment | Required | Industry-specific pain |
| Founding year | Enrichment | Optional | Stage context |
| Current team size | LinkedIn/enrichment | High | Hiring pressure signal |
| Recent hires | LinkedIn | High | Velocity indicator |
| Tech stack | Job posts/enrichment | Medium | Technical resonance |
| Investor names | Press release | Medium | Social proof angle |

### 2. FOUNDER-LEVEL DATA

| Data Point | Source | Priority | Use Case |
|------------|--------|----------|----------|
| Founder name(s) | Press release | Required | Personalization |
| Founder role(s) | LinkedIn | Required | Routing to correct person |
| LinkedIn URL | Exa/enrichment | Required | Research + outreach |
| Email address | Perplexity | High | Direct outreach |
| Prior startups | LinkedIn | Medium | Pattern recognition |
| Technical background | LinkedIn | Medium | CTO vs business founder |
| Public statements | YouTube/podcasts | High | Founder voice matching |
| Content themes | Social media | Medium | Interest alignment |

### 3. DECISION MAKER ROLES

| Role | Priority | Angle |
|------|----------|-------|
| CEO / Co-founder | High | Strategic, growth, execution pressure |
| CTO / Technical Co-founder | High | Technical talent, team quality, speed |
| VP Engineering | High | Engineering velocity, team scaling |
| Head of HR / People Ops | Medium | Hiring process, candidate quality |
| COO / Chief of Staff | Medium | Operations, team efficiency |
| CFO | Low | Budget allocation (if relevant) |

### 4. HIRING PRESSURE SIGNALS

| Signal | Detection Method | Weight |
|--------|------------------|--------|
| Open engineering roles | Job boards, careers page | Strong |
| Multiple AI/ML roles | Job posts | Very Strong |
| "Urgently hiring" language | Job posts | Very Strong |
| Recruiter roles posted | Job boards | Strong |
| Team size doubled recently | LinkedIn | Strong |
| Funding just closed (< 30 days) | Press date | Very Strong |
| Series A/B (high growth stage) | Press release | Strong |
| Seed (team building stage) | Press release | Medium |

### 5. FOUNDER PAIN SIGNALS (From Knowledge Base)

| Pain Category | Example Phrases | Emotional Tone |
|---------------|-----------------|----------------|
| Time pressure | "We needed to hire yesterday" | Urgency |
| Quality concerns | "Finding A-players is impossible" | Frustration |
| Scaling fear | "Can't grow fast enough" | Anxiety |
| Team dynamics | "Culture fit matters more than skills" | Protective |
| Investor pressure | "Board expects us to 3x the team" | Stress |
| Bad hire trauma | "One bad hire cost us 6 months" | Caution |
| Founder burden | "I spend 60% of my time recruiting" | Exhaustion |
| Market competition | "Big tech is outbidding us on talent" | Helplessness |

---

## Research Workflow

### Stage 1: Trigger Detection

**Source 1: RSS Feeds (Every 15 min)**
- TechCrunch
- VentureBeat
- PR Newswire
- BusinessWire

**Source 2: Tavily Search (Daily)**
- Query: "startup funding announcement" + geographic filters
- Covers additional press outlets

**Source 3: Manual Input**
- Jorge finds a company, enters URL
- System enriches and generates draft

### Stage 2: Company Enrichment

```python
# Enrichment cascade
1. Parse press release → company, amount, round, industry
2. Tavily search → validate + expand context
3. Exa neural search → find LinkedIn company page
4. Perplexity → deep research on company, product, market
```

### Stage 3: Decision Maker Discovery

```python
# Multi-source decision maker search
1. Exa search: "{company} CEO OR CTO OR founder LinkedIn"
2. Perplexity: "Who are the founders of {company}?"
3. LinkedIn company page → employees by role
4. Combine and deduplicate
5. Find email via Perplexity
```

### Stage 4: Pain Intelligence Query

```python
# Query founder pain knowledge base
1. Match by: industry, stage, region
2. Retrieve top 5 relevant pain phrases
3. Retrieve emotional context
4. Inject into email generation prompt
```

### Stage 5: Email Generation

```python
# Role-specific generation
for decision_maker in company.decision_makers:
    pain_context = query_pain_kb(company.industry, company.stage, company.region)

    email = generate_email(
        template=get_template(decision_maker.role),
        company=company,
        person=decision_maker,
        pain_context=pain_context,
        language=detect_language(company.region)
    )

    create_gmail_draft(email)
```

---

## Founder Pain Knowledge Base

### Purpose
Store and query real founder language extracted from podcasts and YouTube interviews to make outreach feel authentic and resonant.

### Data Model

```python
class FounderPainEntry:
    source_url: str           # YouTube/podcast URL
    founder_name: str         # Who said it
    company: str              # Their company
    industry: str             # SaaS, AI, Fintech, etc.
    stage: str                # Seed, Series A, B, C
    region: str               # Spain, EU, US

    # Extracted content
    quote: str                # Exact phrase (< 100 words)
    pain_category: str        # Hiring, scaling, time, quality, etc.
    emotional_tone: str       # Urgent, frustrated, anxious, hopeful
    context: str              # What they were discussing

    # Metadata
    timestamp: str            # When in video
    extracted_date: date
    embedding: vector         # For semantic search
```

### Query Patterns

1. **By Industry + Stage**: "Show me pain from Series A AI founders"
2. **By Pain Category**: "Show me quotes about hiring pressure"
3. **By Emotional Tone**: "Show me urgent/stressed quotes"
4. **By Region**: "Show me Spanish founder quotes"
5. **Semantic Search**: "Founders talking about competing with big tech for talent"

### Sources to Scrape

**Priority 1: Spanish-Speaking Channels**
- Startup-focused podcasts from Spain
- Spanish founder interview channels
- European tech news in Spanish

**Priority 2: European Channels**
- EU startup ecosystem content
- London/Berlin tech scene interviews
- Y Combinator Europe content

**Priority 3: US Channels**
- This Week in Startups
- Y Combinator
- a]6z podcasts
- Founder interview channels

---

## Email Generation Principles

### Core Philosophy
> "Write as if you've lived their chaos, not observed it."

### Do's
- Reference specific, current events (funding, hiring signals)
- Use language patterns from pain knowledge base
- Acknowledge the emotional reality of post-funding
- Position Jorge as relief from burden, not a vendor
- Keep it short (< 150 words)
- One clear CTA

### Don'ts
- Don't assume problems they haven't signaled
- Don't use generic sales language
- Don't over-personalize with creepy specifics
- Don't mention competitors
- Don't promise unrealistic outcomes
- Don't send without Jorge's review

### Template Selection Logic

| Condition | Template |
|-----------|----------|
| CEO + Series A/B | Growth pressure angle |
| CTO + AI company | Technical talent angle |
| HR lead + Multiple roles open | Hiring burden relief |
| Spanish company | Spanish template |
| Recent (< 7 days) funding | Timing-specific angle |
| Prior startup founder | Experienced-founder angle |

---

## Success Metrics

### Jorge's Perspective
| Metric | Target | Why It Matters |
|--------|--------|----------------|
| Research time per company | < 5 min | Time is money |
| Email drafts feeling personal | 90%+ | Conversion depends on this |
| Replies to outreach | 10-15% | Quality signal |
| Meetings booked | 5-8% | Revenue driver |

### Prospect's Perspective
| Indicator | Detection Method |
|-----------|------------------|
| "How did you know?" replies | Manual tracking |
| Immediate positive replies | < 24h response |
| Referrals to colleagues | Email content |
| Unsubscribe rate | Should be < 1% |

### System Perspective
| Metric | Target | Alert If |
|--------|--------|----------|
| Funding articles found/day | 5-15 | < 3 for 2+ days |
| Enrichment success rate | 85%+ | < 70% |
| Decision maker found rate | 80%+ | < 60% |
| Email generation success | 95%+ | < 90% |
| API errors | < 5% | > 10% |

---

## Risk Mitigation

### Risk 1: Over-Personalization (Creepy)
**Mitigation:** Only reference public information. Never mention private details, family, or unverified data.

### Risk 2: False Assumptions
**Mitigation:** Use conditional language ("If you're like most founders..."). Never assume a problem exists.

### Risk 3: Stale Data
**Mitigation:** Check funding date. If > 60 days old, adjust messaging (they've likely started solving the problem).

### Risk 4: Wrong Contact
**Mitigation:** Always verify role and company match before drafting. Include confidence score.

### Risk 5: Spam Perception
**Mitigation:** Low volume, high quality. Max 5-10 companies/day. Never auto-send.

### Risk 6: API Rate Limits
**Mitigation:** Key rotation (3-4 keys per API). Exponential backoff. Daily quota tracking.

---

## Execution Scripts (Existing + New)

### Existing Tools
| Script | Purpose |
|--------|---------|
| `jorge_funding_outreach.py` | Full pipeline: find → enrich → draft |
| `jorge_icp_funding_research.py` | Deep research on ICP companies |
| `funding_rss_monitor.py` | RSS feed monitoring |
| `draft_funding_proposal.py` | Basic proposal drafting |
| `send_funding_proposal.py` | Gmail draft creation |

### New Tools (To Build)
| Script | Purpose |
|--------|---------|
| `scrape_founder_youtube.py` | Scrape YouTube transcripts |
| `extract_founder_pain.py` | Extract pain signals from transcripts |
| `query_pain_kb.py` | Query pain knowledge base |
| `populate_pain_kb.py` | Seed/update knowledge base |

---

## Automation Schedule

| Task | Frequency | Method |
|------|-----------|--------|
| RSS monitoring | Every 15 min | GitHub Actions |
| Tavily search | Daily 9am | GitHub Actions |
| Pain KB update | Weekly | Manual trigger |
| Email draft generation | On trigger | Immediate |
| System health check | Daily | Slack alert |

---

## Next Steps

1. ✅ System blueprint (this document)
2. 🔲 Build YouTube transcript scraper
3. 🔲 Build pain extraction pipeline
4. 🔲 Set up Supabase knowledge base
5. 🔲 Integrate pain KB into email generation
6. 🔲 Test end-to-end flow
7. 🔲 Deploy automation

---

*Last Updated: 2026-02-01*
*Owner: Florian (automation) + Jorge (outreach)*
