New
Super Agent
Home
AI Inbox
Hub
AI Drive
EMAIL PERSONALIZATION EXAMPLE 4
Share
take this in and run the below instructions on this specific email copy for a real company we reached out to or at least drafted an email for: 


--- FUNDING LEAD ---
Company: EV
Amount: $6.0M
Round: Series D
Article: https://www.businesswire.com/newsroom/subject/funding

Decision Maker: there
Role: Founder
LinkedIn:
Email:
---

PROPOSAL TO SEND:

Hi there,

Saw the news about EV's funding round ($6.0M Series D) - congratulations! That's a big milestone.

I work with recently funded startups to help them scale their tech teams quickly without the typical hiring headaches. After a raise, most founders I talk to are dealing with:

- Pressure to ship faster while hiring is slow
- Need for senior talent but can't wait 3-6 months to find them
- Wanting to keep burn low while still building

We provide **Agile Tech Pods** - full-stack development teams that can start in 2 weeks, not 2 months. You get experienced devs, a PM, and tech lead - all with complete transparency and work tracking.

Would a quick 15-minute call make sense to see if there's a fit?

Best,
Jorge

P.S. Article I saw: https://www.businesswire.com/newsroom/subject/funding



---

## **B.) PROMPT: Deep Research on Real Company (Example for MVP Training)**

```markdown
# TASK: Deep Research on [COMPANY NAME] for Personalized Outreach

## CONTEXT
You are researching a recently funded startup to build a hyper-personalized, 3-paragraph cold email (max 100 characters per paragraph) on behalf of Jorge Morado. This research will serve as the **gold standard example** to train the automated workflow on "what good looks like."

---

## COMPANY TO RESEARCH
**Company Name**: [INSERT COMPANY NAME]
**Funding Round**: [e.g., Series A]
**Funding Amount**: [e.g., $1.5M]
**Funding Date**: [e.g., January 15, 2026]
**Source Article**: [INSERT URL]

---

## RESEARCH OBJECTIVES

### PHASE 1: COMPANY INTELLIGENCE (15 minutes)

#### 1.1 Company Overview
- **Full legal name** and any DBAs/trade names
- **Industry/sector** (be specific: not just "SaaS" but "Vertical SaaS for restaurants")
- **B2B or B2C?**
- **Target customer** (ICP: who do they sell to?)
- **Mission statement** (in their own words from About page)
- **Value proposition** (what outcome do they promise customers?)
- **Product/service description** (what do they actually do?)
- **Founding date**
- **Current headcount** (from LinkedIn or Crunchbase)
- **Headquarters location** (city, region, country)
- **Remote/hybrid/in-office policy** (if mentioned)

#### 1.2 Funding & Growth Signals
- **Total funding raised to date**
- **Previous funding rounds** (if any: dates, amounts, investors)
- **Lead investor(s) for this round** (names, why this matters)
- **Valuation** (if public)
- **Use of funds** (what did they say they'll spend the money on? hiring? product? expansion?)
- **Hiring velocity**: 
  - Open job postings (count, roles, seniority)
  - **Priority roles** (e.g., 3 PM roles open = scaling product team)
  - Recent hires in last 30 days (from LinkedIn)
  - Headcount growth rate (%)

#### 1.3 Company Evolution & Pivot History
- **Has the company pivoted?** (previous product/market, why they changed)
- **Previous names or brands** (if applicable)
- **Major product milestones** (launches, versions, features)
- **Press mentions** (last 90 days: awards, partnerships, customer wins)

#### 1.4 Technology & Tools
- **Tech stack** (from BuiltWith, Wappalyzer, or job postings):
  - Engineering stack (languages, frameworks)
  - Marketing tools (CRM, email, analytics)
  - Sales tools (CRM, outreach platforms)
  - Collaboration tools (Slack, Notion, etc.)
- **Competitor tools they use** (signals pain points or switching opportunities)

#### 1.5 About Page & Mission Alignment
- **Origin story** (how/why was the company founded?)
- **Team culture indicators** (values, perks, "we believe..." statements)
- **Notable team members** (advisors, board members, investors with operational involvement)

---

### PHASE 2: FOUNDER/DECISION-MAKER INTELLIGENCE (20 minutes per person)

**Research 3 decision-makers**: CEO, CTO, Head of HR/Talent (if exists)

For EACH person, extract:

#### 2.1 Professional Identity
- **Full name**
- **Current title** (exact wording from LinkedIn)
- **Email address** (find via Apollo, Hunter, Perplexity, ExaTabli, or pattern-match from company domain)
- **LinkedIn URL**
- **Years in current role**
- **Previous companies** (last 3 roles: company, title, timeframe)
- **Total years of experience**
- **Notable achievements** (awards, press mentions, patents, publications)

#### 2.2 Educational Background
- **University/college** (name, location)
- **Degree(s)**
- **Graduation year** (approximate if not listed)
- **Certifications or professional development**
- **Greek life, clubs, or notable programs** (potential connection points)

#### 2.3 Geographic & Location Data
- **Current city/region** (from LinkedIn)
- **Previous locations lived** (infer from work history or education)
- **HQ vs remote?** (do they live where the company is based?)

#### 2.4 Social Profiles & Content Activity
- **LinkedIn**:
  - Profile headline (exact wording)
  - About section (key phrases or mission statements)
  - Recent posts (last 30 days: topics, engagement, tone)
  - Recent comments on others' posts (what do they care about?)
  - Endorsements (top 5 skills)
  - Recommendations received (themes)
- **Twitter/X** (if exists):
  - Handle
  - Bio
  - Recent tweets (last 30 days: topics, frequency, tone)
  - Engagement patterns (who they follow, retweet, reply to)
- **Instagram** (if exists):
  - Handle
  - Bio
  - Public/private?
  - If public: content themes (professional? personal? hobbies?)
- **Personal website or blog** (if exists)
- **Podcast appearances, speaking engagements, or media mentions**

#### 2.5 Psychographic & Motivational Signals
- **What are they moving TOWARD?**
  - Career goals (explicit or inferred from content)
  - Company goals (what does success look like for them?)
  - Personal aspirations (family, impact, recognition, wealth, freedom, etc.)
- **What are they moving AWAY FROM?**
  - Frustrations or pain points mentioned in posts/interviews
  - Challenges they've called out publicly
  - Previous negative experiences (layoffs, failed startups, burnout, etc.)
- **Decision drivers** (what motivates this person?):
  - Family (references to spouse, kids, work-life balance)
  - Love/belonging (community, relationships, team culture)
  - Relevance/significance (industry recognition, thought leadership)
  - Security/stability (risk-averse language, emphasis on financial health)
  - Growth/learning (curiosity, experimentation, "always learning" mindset)
  - Impact/legacy (changing the world, helping others)

#### 2.6 LinkedIn Post Deep Dive (Most Recent Post)
For the **most recent LinkedIn post** (within last 30 days):
- **Date posted**
- **Full text** (copy/paste)
- **Topic/theme** (what's it about?)
- **Tone** (excited, reflective, analytical, frustrated, celebratory, etc.)
- **Engagement** (likes, comments, shares)
- **Why did they share this?** (infer motivation: educate, celebrate, vent, recruit, build credibility, etc.)
- **Connection opportunity**: Can Jorge reference this authentically in outreach?

#### 2.7 Network & Connection Data
- **Mutual connections with Jorge** (if LinkedIn access available)
- **Shared groups or communities**
- **Notable connections** (investors, advisors, other founders Jorge might know)
- **Potential warm intro paths** (2nd or 3rd degree connections to Jorge)

---

### PHASE 3: JORGE ↔ FOUNDER MATCHING (10 minutes)

Using Jorge's profile (from Prompt A), identify **ALL possible connection points**:

#### 3.1 Tier 1 Matches (Strongest Hooks)
- [ ] **Mutual connection** (name: _____, context: _____)
- [ ] **Direct work overlap** (same previous company: _____)
- [ ] **Recent LinkedIn post** (topic: _____, hook: _____)
- [ ] **Recent funding** (within 48 hours? Yes/No)
- [ ] **Hiring signal** (open role Jorge can speak to: _____)

#### 3.2 Tier 2 Matches (Solid Hooks)
- [ ] **University overlap** (school: _____, years: _____)
- [ ] **Location overlap** (city/region: _____, Jorge's tie: _____)
- [ ] **Previous company similarity** (founder worked at X, Jorge worked at Y, both in same industry)
- [ ] **Industry alignment** (Jorge's expertise in _____ matches founder's sector)
- [ ] **Career trajectory parallel** (both started in _____, moved to _____)

#### 3.3 Tier 3 Matches (Contextual Hooks)
- [ ] **Mission alignment** (founder's mission: _____, Jorge's values: _____)
- [ ] **Problem-solution fit** (founder's challenge: _____, Jorge's expertise: _____)
- [ ] **Tech stack** (they use _____, Jorge has experience with _____)
- [ ] **Shared interest** (hobby, content topic, thought leadership area)

#### 3.4 Case Study Match
- [ ] **Does Jorge have a case study relevant to this founder's situation?**
  - **If yes**: Client: _____, Challenge: _____, Outcome: _____, Relevance score (1-10): _____

---

### PHASE 4: PERSONALIZATION HOOK SYNTHESIS (5 minutes)

Based on matching analysis, select the **TOP 2 HOOKS** to use in the email:

**Hook 1** (Primary):
- **Type** (e.g., recent LinkedIn post, location overlap, mutual connection)
- **Exact reference** (e.g., "Loved your post on [topic]" or "Also based in [city]" or "[Mutual] suggested I reach out")
- **Why this works** (1 sentence: connects Jorge's expertise to founder's current need)

**Hook 2** (Secondary/Bridge):
- **Type**
- **Exact reference**
- **Why this works**

---

## OUTPUT FORMAT

Deliver research as a **structured document** with:

### SECTION 1: COMPANY PROFILE
```json
{
  "company_name": "...",
  "funding_round": "...",
  "funding_amount": "...",
  "funding_date": "...",
  "industry": "...",
  "mission": "...",
  "target_customer": "...",
  "headquarters": "...",
  "headcount": X,
  "open_roles": [
    {"role": "...", "seniority": "...", "posted_date": "..."}
  ],
  "tech_stack": ["...", "..."],
  "recent_news": ["...", "..."],
  "about_page_insights": "..."
}
SECTION 2: DECISION-MAKER PROFILES (3 People)
Person 1: CEO

Copy{
  "name": "...",
  "title": "...",
  "email": "...",
  "linkedin": "...",
  "education": {"university": "...", "degree": "...", "year": "..."},
  "location": "...",
  "previous_roles": ["...", "...", "..."],
  "social_profiles": {
    "linkedin": "...",
    "twitter": "...",
    "instagram": "..."
  },
  "recent_linkedin_post": {
    "date": "...",
    "text": "...",
    "topic": "...",
    "tone": "...",
    "motivation": "..."
  },
  "psychographic_signals": {
    "moving_toward": ["...", "..."],
    "moving_away_from": ["...", "..."],
    "decision_drivers": ["...", "..."]
  },
  "mutual_connections": ["..."],
  "potential_warm_intro": true/false
}
Person 2: CTO (same schema)

Person 3: Head of HR (same schema)

SECTION 3: MATCHING ANALYSIS
Tier 1 Hooks:

[List all with context]
Tier 2 Hooks:

[List all with context]
Tier 3 Hooks:

[List all with context]
Recommended Hooks for Email:

Primary Hook: [Exact wording + why it works]
Secondary Hook: [Exact wording + why it works]
Relevant Case Study:

Jorge helped [Client] in [Location] solve [Challenge], resulting in [Outcome]. Relevance to this founder: [1-2 sentences].
DELIVERABLE
A single comprehensive research report titled: "[COMPANY_NAME]_Outreach_Research_Feb2026.pdf"

This will serve as the reference example for the automated workflow to replicate.


---

## **C.) PROMPT: Deep Research on Email Architecture (3 Paragraphs, 100 Chars Each, Loom CTA)**

```markdown
# TASK: Research & Design Optimal Cold Email Architecture for Funded Startups

## OBJECTIVE
Research best practices for ultra-concise, high-converting cold emails to recently funded startup founders, then design a 3-paragraph template (max 100 characters per paragraph) with a Loom video CTA.

---

## RESEARCH QUESTIONS

### 1. ULTRA-SHORT EMAIL EFFECTIVENESS
- **What does the data say about email length and reply rates?**
  - Find case studies/benchmarks comparing short (50-150 chars) vs medium (150-300 chars) vs long (300+ chars) emails
  - Identify optimal length for cold outreach to busy founders (especially post-funding)
  - Research "Twitter-style" cold emails (ultra-concise, punchy)

### 2. PARAGRAPH STRUCTURE FOR BREVITY
- **What's the optimal structure for 3-paragraph emails?**
  - Research Hook-Bridge-CTA vs Hook-Value-CTA vs Hook-Question-CTA frameworks
  - Find examples of successful 3-sentence emails to founders
  - Identify common mistakes in short emails (too vague, too salesy, weak CTA)

### 3. VIDEO CTA EFFECTIVENESS
- **How do video CTAs (Loom, Vidyard, BombBomb) perform vs text CTAs?**
  - Find reply rate data for "Should I send a quick Loom video?" vs "Can we chat?" vs "Interested in learning more?"
  - Research psychological triggers (curiosity, low commitment, personalization) behind video CTAs
  - Identify best practices for positioning video as follow-up vs upfront

### 4. FOUNDER PSYCHOLOGY POST-FUNDING
- **What's the mental state of founders 0-60 days after closing a round?**
  - Research common challenges (hiring, scaling, investor reporting, operational chaos)
  - Identify emotional states (excited, overwhelmed, optimistic, skeptical of vendors)
  - What types of messages cut through the noise during this window?

### 5. CHARACTER COUNT CONSTRAINTS
- **How do character limits (100/paragraph) affect message clarity?**
  - Research SMS/text-style outreach (similar constraints)
  - Find examples of powerful, sub-100-char value propositions
  - Identify what to cut (fluff, adjectives, long intros) and what to keep (specifics, outcomes, names)

### 6. MULTI-CHANNEL CONTEXT (EMAIL → LOOM)
- **What's the best way to set up a video follow-up in the initial email?**
  - Research sequencing: Does the first email mention video, or is video a reply to their response?
  - Find examples of "Should I send you a quick video?" CTAs and their performance
  - Identify objection-handling language (e.g., "2-minute video, no strings attached")

---

## RESEARCH SOURCES TO CONSULT

1. **Case Studies**:
   - Revisit Ambition, Jake Jorgovan, LeadFuze, Crazy Eye, Marco Massaro for email length data
   - Search for "ultra-short cold email case studies" or "Twitter-style cold emails"

2. **Practitioner Content**:
   - RepliQ, Clay, Instantly.ai, Lemlist blogs on email brevity
   - Aaron Shepherd (GrowthFlare) YouTube videos on founder outreach
   - LinkedIn posts from sales leaders testing short vs long emails

3. **Reddit/Forums**:
   - r/sales, r/startups, r/coldemail discussions on email length
   - r/GrowthHacking threads on video CTAs

4. **Academic/Data**:
   - Boomerang, Yesware, or HubSpot studies on email length vs reply rate
   - A/B test results from Outreach.io, Reply.io, or SalesLoft

5. **Video Tools**:
   - Loom, Vidyard, BombBomb case studies or whitepapers on video in sales
   - Testimonials or user stories from founders who responded to video CTAs

---

## ANALYSIS FRAMEWORK

For each research source, extract:
- **Claim**: What does this source say about email length, structure, or video CTAs?
- **Evidence**: What data, case study, or example supports the claim?
- **Relevance**: How does this apply to Jorge's use case (funded startup founders, 0-60 days post-round)?
- **Actionability**: What specific tactic or wording can we adopt?

---

## OUTPUT DELIVERABLE 1: RESEARCH SUMMARY

A **structured report** with:

### FINDING 1: Optimal Email Length for Founders
- **Consensus**: [e.g., "50-150 characters = highest reply rate for busy executives"]
- **Supporting data**: [List 3-5 sources with specific numbers]
- **Contrarian view**: [If any sources disagree, note it]
- **Recommendation**: [e.g., "Aim for 80-100 chars per paragraph"]

### FINDING 2: Best 3-Paragraph Structure
- **Consensus**: [e.g., "Hook (personal) → Value (outcome-focused) → CTA (low-commitment)"]
- **Supporting data**: [List examples and sources]
- **Common mistakes to avoid**: [e.g., "Don't ask for 30-min call in first email"]
- **Recommendation**: [Exact structure to use]

### FINDING 3: Video CTA Performance
- **Consensus**: [e.g., "'Should I send a quick Loom?' increases reply rates by 15-30%"]
- **Supporting data**: [List sources]
- **Optimal phrasing**: [e.g., "Quick 2-min Loom on [topic]?" vs "Can I record a video for you?"]
- **Recommendation**: [Exact CTA wording]

### FINDING 4: Founder Psychology Post-Funding
- **Key insight**: [e.g., "Founders are overwhelmed with vendor pitches but desperate for tactical help with hiring/ops"]
- **What resonates**: [e.g., "Specific outcomes, social proof from similar companies, low-friction offers"]
- **What turns them off**: [e.g., "Long emails, vague value props, pushy sales language"]
- **Recommendation**: [How to position Jorge's outreach]

### FINDING 5: Character Constraints Best Practices
- **What to keep**: [e.g., "Founder's name, funding amount, 1 specific outcome"]
- **What to cut**: [e.g., "Adjectives, long intros, company backstory"]
- **Examples of great <100-char sentences**: [5-10 examples]

---

## OUTPUT DELIVERABLE 2: EMAIL TEMPLATE (3 Paragraphs, 100 Chars Each)

Based on research, design the **gold standard template**:

SUBJECT: [Under 50 chars, personalized hook]

PARAGRAPH 1 (HOOK): [Max 100 characters] [Personalization: funding, LinkedIn post, location, or mutual connection]

PARAGRAPH 2 (VALUE): [Max 100 characters] [Outcome-focused: case study or relevant expertise tied to their need]

PARAGRAPH 3 (CTA): [Max 100 characters] [Low-friction ask: "Should I send a quick Loom on [topic]?" or similar]

Best, Jorge


### TEMPLATE VARIANTS (Create 3)

**Variant 1: Funding-Based Hook**
SUBJECT: Quick Q, [FirstName]

Congrats on the $[Amount] [Round]—exciting milestone.

Helped [Similar Co] scale hiring post-Series A, cut PM onboarding 40%.

Should I send a quick 2-min Loom on how? No strings.

Best, Jorge

*Character counts: P1=56, P2=67, P3=59*

**Variant 2: LinkedIn Post Hook**
SUBJECT: Loved your post on [Topic]

Your take on [Topic] resonates—saw this with [Client].

We solved [Pain] for them post-raise, [Outcome].

Want a quick Loom on our approach? 2 mins, tops.

Best, Jorge

*Character counts: P1=53, P2=51, P3=49*

**Variant 3: Location-Based Hook**
SUBJECT: Fellow [City] founder here

[City]-based too—helped [Local Client] with [Challenge].

Post-[Round], most startups hit [Pain]; we've cracked it.

Should I send a Loom on what worked? Quick 2 min.

Best, Jorge

*Character counts: P1=52, P2=59, P3=56*

---

## OUTPUT DELIVERABLE 3: VIDEO CTA OPTIMIZATION

### Why "Should I send a Loom?" Works
- **Psychological triggers**:
  1. **Curiosity**: "What's in the video?"
  2. **Low commitment**: "It's only 2 minutes, I can always ignore it"
  3. **Personalization signal**: "They're willing to record something just for me"
  4. **Control**: "I get to decide if I want it"

### Optimal Phrasing (Based on Research)
- ✅ **BEST**: "Should I send a quick 2-min Loom on [specific topic]?"
  - *Why*: Specific topic = relevant; 2 min = not a burden; question = low pressure
- ⚠️ **GOOD**: "Want a quick video walkthrough?"
  - *Why*: Less specific, but still low commitment
- ❌ **AVOID**: "Can we schedule a video call?"
  - *Why*: High commitment, sounds like a sales pitch

### Follow-Up If They Say Yes
Great! Here's a quick 2-min Loom I recorded just for you: [Link]

Shows how we helped [Similar Co] solve [Pain] post-[Round].

Worth a 15-min chat to see if it fits? [Calendar link]


### Follow-Up If No Reply (Day 3)
Sent this a few days ago—figured I'd just record the Loom anyway.

Here's the 2-min breakdown: [Link]

If it's useful, let's chat. If not, no worries.


---

## QUALITY CHECKS

Before finalizing:
- [ ] Each paragraph in all templates is ≤100 characters
- [ ] Subject line is ≤50 characters
- [ ] At least 3 variants created for different hook types
- [ ] CTA consistently mentions "Loom" and "2 minutes"
- [ ] Research summary cites at least 5 credible sources
- [ ] Templates avoid jargon, adjectives, and filler words
- [ ] Tone is warm, confident, not pushy

---

## DELIVERABLE

A **comprehensive document** titled:
**"Jorge_Outreach_Email_Architecture_Research_Feb2026.pdf"**

Including:
1. Research summary (5 findings)
2. 3 email template variants (with character counts)
3. Video CTA optimization guide
4. Follow-up messaging scripts
SUMMARY: 3-PART PROMPTING SYSTEM FOR 30-HOUR MVP
Prompt	Purpose	Output	Time Est.
A	Extract Jorge's personal profile from 42 transcripts	Jorge_Connection_Database.json	3-4 hours
B	Deep research on 1 real company (example)	[Company]_Outreach_Research.pdf	1-2 hours
C	Research email architecture + design templates	Email_Architecture_Research.pdf	2-3 hours
Total Research Time: 6-9 hours
Remaining Time for Implementation: 21-24 hours

These prompts are ready to run through your deep research model. Once you have the outputs, we'll use them to:

Build the Jorge ↔ Founder matching algorithm
Train the automated enrichment workflow (Apollo → Perplexity → Clay)
Generate draft emails in Jorge's inbox with all research attached
Prep multi-channel outreach (email, LinkedIn, Instagram DMs)
Ready to execute? Let me know if you'd like me to refine any of these prompts further or if you want me to start running them myself!
I'll execute this comprehensive research project systematically. Let me break this down into the three core research phases and deliver actionable outputs.

⚠️ CRITICAL ISSUE IDENTIFIED: The funding lead you provided is incomplete - "EV" with a $6M Series D and a generic BusinessWire URL won't yield real research. I'll need either:

A real company name/complete article URL, OR
Permission to proceed with Prompt C (Email Architecture Research) first since it's company-agnostic
RECOMMENDED APPROACH: Start with Prompt C (email architecture research) immediately, then you can provide a real company for Prompt B.

🎯 EXECUTION PLAN
Phase 1: Email Architecture Research (Prompt C) ⬅️ START HERE
This is company-agnostic and can be completed immediately

Phase 2: Company Deep Dive (Prompt B)
Requires valid company information

Phase 3: Synthesis & Template Generation
Combines findings into actionable framework

🚀 SHALL I PROCEED WITH PHASE 1 (EMAIL ARCHITECTURE RESEARCH)?
This will involve:

Analyzing 15-20 authoritative sources on cold email best practices
Extracting data on ultra-short email performance (100 char/paragraph)
Researching video CTA effectiveness (Loom, Vidyard)
Understanding founder psychology post-funding
Designing 3 optimized email variants
Creating follow-up sequences
Estimated time: 45-60 minutes of research + synthesis

Deliverable: Complete email architecture guide with templates, character counts, psychological triggers, and multi-channel follow-up strategy

📋 MEANWHILE: FOR PROMPT B (COMPANY RESEARCH)
Please provide ONE of the following:

Option A: Complete company details

Company Name: [Full name]
Funding Article URL: [Complete URL]
Funding Amount: [e.g., $6.0M]
Round Type: [e.g., Series D]
Announcement Date: [e.g., Jan 15, 2026]
Option B: Just a company name (I'll find the rest)

Company Name: [e.g., "Acme Corp" or "TechStartup Inc"]
Option C: Pick from recent funding announcements (I can search for latest funded companies in a specific sector)

SHALL I START WITH PHASE 1 (EMAIL ARCHITECTURE RESEARCH) NOW?

Type "Yes, start Phase 1" and I'll begin immediately while you source the real company info for Phase 2.

Yes, start Phase 1 - begin the email architecture research now
Here's the complete funding lead info: [Company Name], [Amount], [Round Type], [Article URL] - run all 3 phases
Skip to Phase 3 - create 5 draft outreach emails for Jorge's review with placeholder company info
Search for the latest Series A-C funding rounds in [specific industry] from the past 30 days and prepare outreach research
Super Agent
Team Chat
Ask anything, create anything
Tool IconTool Icon
