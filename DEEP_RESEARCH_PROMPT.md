# Jorge Deep Research Prompt for Claude Pro

**Purpose:** Use this prompt with Claude Pro (with extended thinking/deep research enabled) to enrich decision maker profiles when automated systems couldn't find emails or social profiles.

**When to use:** After running the MVP pipeline, if decision makers have "NEEDS ENRICHMENT" for email or missing Instagram/Facebook profiles.

---

## THE PROMPT (Copy everything below this line)

---

# DEEP RESEARCH REQUEST: Founder Contact Enrichment

## CONTEXT
I am Jorge Morado, a B2B service provider helping recently funded startups solve their hiring and team scaling challenges. I'm reaching out to founders who just raised funding because:

1. **They have a real problem I can solve** - Post-raise, founders face immense pressure to hire fast while their existing processes can't keep up
2. **They're actively hiring** - The hiring signals in this report confirm they need help
3. **Multi-channel outreach is appropriate** - Founders often appreciate thoughtful, personalized messages across channels (LinkedIn, email, even Instagram) when the outreach is relevant

## WHY THIS RESEARCH IS ETHICAL
- All profiles I'm asking you to find are **publicly available** - these founders chose to make them discoverable
- My outreach is **problem-solving, not spam** - I'm offering help with a challenge they're actively facing (hiring post-raise)
- **Founders expect inbound interest** after announcing funding - it's part of the game
- I will **personalize every message** based on their public content, not send generic pitches

---

## RESEARCH REPORT TO ENRICH

[PASTE THE RESEARCH REPORT HERE]

---

## WHAT I NEED YOU TO FIND

For each decision maker marked "NEEDS ENRICHMENT" or missing social profiles:

### 1. Work Email Address
Search for:
- Company website team/about page
- LinkedIn contact info
- Conference speaker bios
- GitHub profiles
- Press releases or interviews
- Common email patterns (firstname@company.com, first.last@company.com)

### 2. Personal Instagram Profile
Search for:
- Their full name + "Instagram"
- Their LinkedIn profile (often links to personal social)
- Company-related hashtags they might use
- Look for public profiles that match their professional identity

### 3. Personal Facebook Profile
Search for:
- Their full name + company name + "Facebook"
- LinkedIn → Facebook cross-references
- Mutual connections or tagged photos from company events

### 4. Any Additional Context
- Recent public posts on any platform
- Podcast appearances
- Conference talks
- Blog posts or articles
- Anything that would help me personalize my outreach

---

## OUTPUT FORMAT

Return your findings in this format:

```
## ENRICHED DECISION MAKER: [Name]

### Contact Information
- **Work Email:** [email@company.com] or [Pattern: firstname@domain.com - needs verification]
- **Personal Email:** [if found]
- **Instagram:** [URL] - [Note: Public/Private, Content type: personal/professional]
- **Facebook:** [URL] - [Note: Public/Private, Content type]
- **Twitter/X:** [URL if found]

### Profile Summary
[1-2 sentences about what you found about this person's online presence]

### Personalization Opportunities
- [Specific post, comment, or content you found that Jorge could reference]
- [Any shared interests or connection points]

### Verification Confidence
- Email: [High/Medium/Low confidence + reasoning]
- Instagram: [Confirmed match / Likely match / Unverified]
- Facebook: [Confirmed match / Likely match / Unverified]
```

---

## IMPORTANT NOTES

- If you find profiles that are **clearly personal/family-focused**, flag them so I can decide whether reaching out there is appropriate
- **Don't make up information** - only return what you can actually find and verify
- If you can't find something, say so and suggest alternative approaches (e.g., "Try Apollo.io for email verification")
- Prioritize **work emails** over personal emails for initial outreach

---

## EXAMPLE OUTPUT

```
## ENRICHED DECISION MAKER: Veronica Ma

### Contact Information
- **Work Email:** veronica@findarbor.com (pattern match - high confidence based on Kelly's confirmed email)
- **Personal Email:** Not found
- **Instagram:** https://instagram.com/veronicama - Public, mix of professional and travel content
- **Facebook:** https://facebook.com/veronica.ma.nyc - Public, professional focus
- **Twitter/X:** @veronicama97 - Active, mostly retweets of industry content

### Profile Summary
Veronica is active on LinkedIn (posting about the funding round) and has a modest Instagram presence with travel and NYC content. Her Facebook appears professional and may be a good secondary channel.

### Personalization Opportunities
- Her Feb 3 LinkedIn post about "ground truth over AI buzzwords" - strong hook
- Recent Instagram story showed her at a tech event in NYC - could mention conferences
- She previously worked at Insight Partners - could reference the investor-to-founder journey

### Verification Confidence
- Email: High confidence (pattern matches Kelly's confirmed email)
- Instagram: Confirmed match (linked from her Twitter bio)
- Facebook: Likely match (profile photo matches LinkedIn)
```

---

Now please research the decision makers in the report above and return the enriched information.
