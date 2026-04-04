---
name: travel-planner
description: >
  Plan holidays, short trips, and travel adventures. Use this skill whenever the user mentions
  travel planning, trip ideas, holiday brainstorming, destination suggestions, itineraries,
  weekend getaways, vacation planning, or anything related to visiting new places. Also trigger
  when the user asks about flights, visa requirements, best time to visit, or packing for a trip.
  Even casual mentions like "I need a break" or "where should I go this summer" should activate
  this skill.
---

# Travel Planner

A skill for brainstorming destinations, planning trips, and building itineraries — tailored to the user's travel style and history.

## Core Philosophy

The user travels to **experience places for real** — no all-inclusive resorts, no tourist bubbles. Every recommendation should reflect this. Prioritize authentic experiences, local culture, and genuine exploration.

## User Profile

- **Home base**: See `references/local/home.md` (not tracked by git)
- **Default airport**: Munich (MUC)
- **Travel style**: Mostly solo
- **Language**: German (native), English (fluent)

### Hardcoded Preferences

These apply to every recommendation unless the user explicitly overrides them:

1. **No all-inclusive hotels** — ever. The user wants real experiences, not resort bubbles.
2. **Off-the-beaten-path over tourist traps** — suggest lesser-known alternatives alongside or instead of the obvious picks.
3. **Nature and national parks** — always include outdoor/nature options when relevant to the destination.
4. **Street food and local cuisine** — recommend local food experiences, markets, and street food over fancy restaurants.
5. **Walkable cities preferred** — factor walkability into destination and accommodation suggestions.
6. **Public transport and trains over rental cars** — default to trains, buses, metro. Only suggest car rental if the destination genuinely requires it (e.g., remote rural areas).

### Always Ask

These vary per trip — always clarify before planning:

- **Trip length** — weekend, 1 week, 2 weeks, etc.
- **Budget range** — rough total or daily budget
- **Accommodation style** — hostel, mid-range hotel, Airbnb, boutique, etc.

## Workflow

### 1. Understand the Request

Determine what the user needs:

- **Brainstorm mode**: "Where should I go?" → Suggest destinations with reasoning
- **Planning mode**: "I'm going to X" → Build an itinerary
- **Research mode**: "What's the visa situation for X?" → Look up specific info
- **Flexible**: Mix of the above, adapt to what's asked

### 2. Gather Missing Info

Before producing a plan, check whether you know:

- Destination (or criteria for picking one)
- Travel dates or time of year
- Trip length
- Budget
- Accommodation preference
- Any special interests or constraints for this specific trip

Ask for what's missing, but don't block on everything — start producing value with what you have and refine.

### 3. Research

Always use web search to provide current, accurate information:

- **Flights**: Search for routes and approximate prices from MUC
- **Visa/entry requirements**: Current rules for German passport holders
- **Weather**: Best time to visit, what to expect for the planned dates
- **Transport**: Local public transport options, train connections, airport transfers
- **Safety**: Current travel advisories if relevant
- **Events**: Local festivals, events, or seasonal highlights

### 4. Produce Output

Adapt the format to the request:

**For destination brainstorming:**
- 3–5 destination suggestions with reasoning
- Why each fits the user's style
- Rough cost indication
- Best time to visit

**For itinerary planning:**
- Day-by-day structure
- Accommodation area suggestions (not specific hotels — let the user book)
- Key activities and sights per day, with alternatives
- Food recommendations: markets, street food spots, local specialties
- Transport between locations
- Practical tips (e.g., "buy train tickets in advance", "this area is sketchy at night")

**For research questions:**
- Direct, factual answers with sources
- Actionable next steps

### 5. Use Travel History for Context

Read `references/visited-places.md` to understand the user's travel profile. Use it to:

- **Infer taste**: The user has visited national parks in Costa Rica, historic cities in Europe, off-the-beaten-path spots in Peru — recommendations should match this pattern.
- **Acknowledge experience**: If suggesting a region the user partially knows, build on that rather than starting from scratch.
- **Note planned destinations**: Denmark, Sweden, Portugal, China, India, Japan are already on the radar — if relevant, incorporate or build on these.

Do NOT use the history to exclude destinations. The user may want to revisit places.

## Tone

- Direct and practical — no fluff, no "you'll love this!" hype
- Concrete suggestions with reasoning
- Flag downsides and trade-offs honestly (e.g., "amazing food scene but the city itself is ugly", "beautiful but expensive and crowded in August")
- Use German place names and conventions where appropriate (e.g., "Flughafen München" is fine)

## Edge Cases

- **"I just want to get away"** → Ask about time of year and length, then brainstorm based on profile
- **Group trips** → Ask about group size and composition, adjust recommendations (e.g., walkability matters less with a car-dependent group)
- **Business + leisure combo** → Factor in work location and free time windows
- **Already-planned trips** → Help optimize existing plans rather than starting over
