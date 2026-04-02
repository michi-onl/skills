---
name: wende-spotify-list
description: >
  Automate the monthly update of the German Wikipedia article "Liste der
  meistgestreamten Künstler auf Spotify". Use this skill whenever the user wants
  to update, refresh, or synchronize the German Spotify streaming artists list
  with the English Wikipedia source. Trigger phrases include "Spotify-Liste
  aktualisieren", "monthly Spotify update", "Spotify artists update", "Liste
  aktualisieren", "Spotify list sync", "meistgestreamte Künstler aktualisieren",
  or any mention of updating the Spotify streaming list article. Also trigger when
  the user mentions it's the first of the month and they need to do their
  Wikipedia update, or when they paste Spotify streaming data and want it
  integrated into the German article.
---

# Wende-Spotify-List — Monthly Spotify List Updater

Update the German Wikipedia article "Liste der meistgestreamten Künstler auf
Spotify" by pulling the current English source, identifying changes, merging
them into the existing German article, and producing ready-to-upload wikitext.

The German article is not a translation. It has its own editorial structure,
Germany-specific tables, and data from sources the English article doesn't use.
This skill merges changes rather than regenerating from scratch.

## Before you start

Read these files at the beginning of every run:

1. `wende/references/rules.yaml` — conversion rules for templates, citations,
   namespaces, dates, numbers, typography
2. `wende-spotify-list/references/en.txt` — last known English wikitext
3. `wende-spotify-list/references/de.txt` — current German wikitext

All three paths are relative to the skills directory. The skills directory
is wherever this SKILL.md lives (its parent).

## Scripts

Two helper scripts live in `scripts/`. Use them — they're faster and more
reliable than doing these checks by hand on a 700-line file.

**`scripts/diff_sections.py`** — Compare two wikitext files section-by-section.
Run this in Step 2 to identify what changed in the English article.

```bash
python3 scripts/diff_sections.py references/en.txt /tmp/en_fresh.txt
# Add --json for structured output
```

**`scripts/quality_check.py`** — Validate the final German wikitext. Run this
in Step 5 before outputting. Catches unbalanced braces, unconverted English
templates, wrong number formats, mangled URLs, missing Stand dates.

```bash
python3 scripts/quality_check.py references/de.txt
# Exit code 0 = clean, 1 = errors found. Add --json for structured output.
```

Always run `quality_check.py` on the final output. Fix any errors it reports
before presenting the result to the user. Warnings are advisory — mention them
in the summary but don't necessarily fix them.

## Article structure map

The German article has sections that don't map 1:1 to English. Know what
you're working with before touching anything.

### German sections

| Section | Source | Notes |
|---------|--------|-------|
| Lead (images + intro paragraph) | Both | "Stand MONAT JAHR" date must be updated |
| Meistgestreamte Künstler > Gesamt | ChartMasters | 25 artists, columns: artist, country, streams (Mrd.), song count, 1Mrd/100Mio/10Mio/1Mio thresholds. NOT in English article. |
| Nach Jahr > Weltweit | English article | Maps to "By year" in en |
| Nach Jahr > Deutschland | German-only | Untouched by English changes |
| Nach Jahrzehnt | English article | Maps to "By decade" in en |
| Meiste monatliche Hörer > Übersicht | English article | Maps to "Most monthly listeners". Top 50 in de, top 50 in en. |
| Zeitstrahl der Höchstwerte | English article | Maps to "Timeline of peak monthly listeners" |
| Statistik | German-only | Summary of months at #1 |
| Meiste Follower | German-only | Follower counts from Spotify profiles |
| Siehe auch / Einzelnachweise / Kategorien | Both | Standard footer |

### English-only sections (not carried to German)

- "First 10 years" (2008–2018) — omitted in dewiki
- "Most monthly listeners" rank column — dewiki uses `tabelle-zaehler` auto-numbering instead

## Workflow

### Step 1: Fetch current English source

Use WebFetch to pull the raw wikitext:

```
https://en.wikipedia.org/w/index.php?title=List_of_most-streamed_artists_on_Spotify&action=raw
```

Save to a temporary variable. This is the fresh English source.

### Step 2: Diff against stored English reference

Save the fetched wikitext to a temp file, then run the diff script:

```bash
python3 scripts/diff_sections.py references/en.txt /tmp/en_fresh.txt
```

Review the output. Focus on:

- New rows added to tables (new artists, new years)
- Changed numbers (stream counts, monthly listeners, rankings)
- New or modified prose in the lead or section intros
- New references added
- Rank changes (Up/Down/Steady indicators)
- New sections or structural changes

Summarize the changes for the user before proceeding. Group them by section:
"By year table: no changes", "Monthly listeners: 12 rank changes, 3 new
entries", etc. Ask the user if they want to proceed or adjust anything.

### Step 3: Update each German section

Work through the sections in order. For each section, apply only the changes
identified in Step 2. Preserve all existing German formatting, editorial
choices, and dewiki conventions.

#### 3a: Lead paragraph

- Update "Stand MONAT JAHR" to current month/year
- Incorporate any prose changes from the English lead
- Translate new sentences into encyclopedic German
- Keep existing German phrasing where the English hasn't changed

#### 3b: Gesamt table (ChartMasters)

This table uses data from ChartMasters, not from the English article. The
English article doesn't have this table at all.

- Fetch current data from `https://chartmasters.org/most-streamed-artists-ever-on-spotify/`
  using WebFetch
- Update stream counts, song counts, and threshold numbers for all 25 artists
- Check if the ranking order has changed — if artists swapped positions, reorder
- If a new artist entered the top 25, add them and remove whoever dropped out
- Keep the `tabelle-zaehler` class and German formatting (commas as decimal
  separators, dots as thousands separators)
- Update the "Stand: DATUM" footer to today's date
- Country flag templates stay as-is unless an artist's country data was wrong

#### 3c: Nach Jahr > Weltweit

- Add new year rows if a new Wrapped was released since last update
- Update stream counts in parentheses if they changed
- Convert English wikitext conventions for any new rows using wende rules
- The Deutschland subsection is untouched here — skip it entirely

#### 3d: Nach Jahrzehnt

- Rarely changes. Only update if the English source added a new decade row.

#### 3e: Meiste monatliche Hörer

This is the most labor-intensive section. Monthly listener numbers change
every month.

- The English article's "Most monthly listeners" table has the current data
- For each artist in the table:
  - Update the monthly listener number (convert to German decimal format: 135,02 not 135.02)
  - Update the change indicator: `{{Steady}}` → `{{Unverändert}}`, `{{Up}}` → `{{Gestiegen}}`, `{{Down}}` → `{{Gefallen}}`
  - If an artist is new to the top 50, add them with `{{Neu}}`
  - If an artist dropped out, remove them
  - Keep the German wikilink forms (e.g., `[[Drake (Rapper)|Drake]]` not `[[Drake (musician)|Drake]]`, `[[Sia (Sängerin)|Sia]]` not just `[[Sia]]`)
- Do NOT add a rank column — the German table uses `tabelle-zaehler` for
  auto-numbering
- Update the "Stand: DATUM" footer to today's date
- Update `abruf=` dates in refs to today's date (ISO format: YYYY-MM-DD)

#### 3f: Zeitstrahl der Höchstwerte

- Check if the English "Timeline of peak monthly listeners" section has new
  months or corrections
- Add new month entries, translating month names to German
- Convert any new references using wende rules
- Keep the existing table structure and German column headers

#### 3g: Statistik

- Update month counts if the #1 most-listened artist changed
- Update "Stand MONAT JAHR"

#### 3h: Meiste Follower

This section is German-only and uses Spotify profile data.

- The English article doesn't have a direct equivalent for follower rankings
- If the user provides updated follower data or asks for an update, fetch
  from the Spotify artist profile pages listed in the refs
- Otherwise, leave unchanged and note that follower data needs manual review
- Update the "Stand" date if data was refreshed

### Step 4: Apply wende conversion rules to any new content

For any new text that came from the English source, apply the full wende
conversion pipeline (see `wende/references/rules.yaml`):

1. Remove disposable templates (`{{Short description}}`, `{{Use dmy dates}}`, etc.)
2. Convert citation templates (`{{cite web}}` → `{{Internetquelle}}`, all params)
3. Convert namespaces (`File:` → `Datei:`, `Category:` → `Kategorie:`)
4. Convert image params (`thumb` → `mini`, `right` → `rechts`, `upright` → `hochkant`)
5. Convert number formats (`.` → `,` for decimals, `,` → `.` for thousands)
6. Convert date formats (MDY → DMY, translate month names)
7. Convert wikilinks (known mappings from rules.yaml)
8. Convert typography (`"..."` → `„..."`, em dash → en dash)
9. Add `|sprache=en` to English-language source references
10. Remove params listed under `remove_params` in rules.yaml (`archive-url`, `archive-date`, `url-status`)

Do NOT apply number format conversion inside URLs, ISO dates, DOIs, or ISBNs.

### Step 5: Quality checks

Run the quality check script on the updated German wikitext:

```bash
python3 scripts/quality_check.py references/de.txt
```

Fix any errors before proceeding. Then also manually verify:

- [ ] All `{{` have matching `}}`
- [ ] All `<ref>` have matching `</ref>` or are self-closing
- [ ] No English template names remain (`cite web`, `cite news`, `Infobox`, `Abbr`)
- [ ] No English namespace prefixes (`Category:`, `File:`)
- [ ] No English image params (`thumb`, `right`, `left`, `upright` used as image param)
- [ ] Numbers in prose use German format (comma decimal, dot thousands)
- [ ] URLs are untouched
- [ ] ISO dates in citation params are untouched
- [ ] "Stand" dates are updated to current month/year
- [ ] `tabelle-zaehler` classes preserved on all auto-numbered tables
- [ ] German wikilink forms used throughout (`[[Drake (Rapper)|Drake]]` not `[[Drake (musician)|Drake]]`)
- [ ] Uncertain wikilinks flagged with `<!-- TODO: dewiki-Linkziel prüfen -->`

### Step 6: Output

1. Write the updated German wikitext to `wende-spotify-list/references/de.txt`
2. Write the fetched English wikitext to `wende-spotify-list/references/en.txt`
   (this becomes the baseline for next month's diff)
3. Present a summary to the user:
   - Which sections were updated and what changed
   - Any TODO comments that need manual review
   - Any artists where wikilinks might need checking
   - Whether follower data was refreshed or still needs updating

## German formatting conventions

These are non-negotiable for the German article:

- **Decimal separator**: comma (`116,8` not `116.8`)
- **Thousands separator**: dot (`1.041` not `1,041`)
- **Scale words**: `Milliarden` not `billion`, `Millionen` not `million`
- **Date format**: `1. April 2026` in prose, `2026-04-01` in `abruf=` params
- **Stand dates**: `Stand April 2026` in prose, `Stand: 1. April 2026` in table footers
- **Citations**: `{{Internetquelle|url=...|titel=...|hrsg=...|abruf=...|sprache=en}}`
- **Templates**: `{{Unverändert}}`, `{{Gestiegen}}`, `{{Gefallen}}`, `{{Neu}}`
- **Table classes**: `wikitable sortable tabelle-zaehler`
- **Auto-numbering**: no manual rank column; `tabelle-zaehler` handles it
- **Wikilinks**: Use dewiki article titles (`[[Drake (Rapper)|Drake]]`, `[[BTS (Band)|BTS]]`, `[[Sia (Sängerin)|Sia]]`, `[[Adele (Sängerin)|Adele]]`, `[[Travis Scott (Rapper)|Travis Scott]]`, `[[Pitbull (Rapper)|Pitbull]]`, `[[SZA (Sängerin)|SZA]]`, `[[Alan Walker (Musikproduzent)|Alan Walker]]`, `[[Maluma (Sänger)|Maluma]]`, `[[Chris Brown (Sänger)|Chris Brown]]`, `[[Raye (Sängerin)|RAYE]]`)
- **Small tags**: `<small>(26,6 Milliarden)</small>` not `{{small|(26.6 billion)}}`
- **Country flags**: `{{USA}}`, `{{GBR}}`, `{{CAN}}`, `{{US-PR}}`, `{{COL}}`, `{{KOR}}`, `{{FRA}}`, `{{Barbados}}` etc.

## Handling edge cases

**New artist enters a table**: Check if they already have a German Wikipedia
article. If the dewiki title differs from enwiki (common for disambiguated
names), use the German form. If uncertain, use the English link and mark with
`<!-- TODO: dewiki-Linkziel prüfen -->`.

**Artist drops from a table**: Remove the row cleanly. If they had a named ref
(`<ref name="...">`) used elsewhere in the article, keep the ref definition
where it's first used and convert other uses to `<ref name="..."/>`.

**ChartMasters data unavailable**: Note this in the summary and skip the Gesamt
table update. The user can provide the data manually.

**Conflicting data between sources**: Flag it. Use the English Wikipedia data
for sections sourced from English, ChartMasters for the Gesamt table, and
Spotify profiles for monthly listeners/followers. Note any discrepancies.
