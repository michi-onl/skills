---
name: wende
description: >
  Convert Wikipedia wikitext syntax between English and German. Use whenever the user
  (1) pastes English or German wikitext and wants the syntax converted, (2) asks to
  convert templates, citations, or formatting between enwiki and dewiki conventions,
  (3) wants to add or update conversion rules, or (4) needs prose translated while
  preserving wikitext markup. Also trigger when the user mentions "Wikitext konvertieren",
  "enwiki to dewiki", "Vorlagen umwandeln", or pastes raw wikitext with English templates
  like {{cite web}} or German templates like {{Internetquelle}}. This skill handles
  syntactic conversion only — for creating complete German Wikipedia articles from
  English sources, use the wiki-artikel skill instead.
---

# Wende – Wikipedia Wikitext Converter

Convert Wikipedia wikitext syntax between English and German. This skill handles the
mechanical, rule-based part of conversion: templates, citations, formatting, numbers,
dates, namespaces. It does not restructure articles or make editorial decisions — that
is what the wiki-artikel skill does.

## When to use Wende vs. Wiki-Artikel

| Situation | Skill |
|-----------|-------|
| "Convert these cite templates to Internetquelle" | **Wende** |
| "Turn this English article into a dewiki article" | **Wiki-Artikel** (which uses Wende internally) |
| "Fix the formatting on this German wikitext" | **Wende** |
| "Add a conversion rule for template X" | **Wende** |

Wende is a tool. Wiki-Artikel is a workflow that calls on Wende as one of its steps.

## How Conversion Works

Claude applies the rules from `references/rules.yaml` manually during conversion.
The YAML file is the single source of truth for all mappings. Always consult it —
don't rely on memory for template names or parameter mappings, because the file may
have been updated since the last conversation.

Read `references/rules.yaml` at the start of every conversion task.

## Conversion Workflow

### Step 1: Determine direction

Identify whether the conversion goes en→de or de→en. If the user doesn't specify,
infer from the wikitext content (English template names → en→de, German ones → de→en).

### Step 2: Apply syntax rules

Work through the rule categories in this order. The order matters because some
transformations depend on others (e.g., citation parameters only make sense after
the template name has been converted).

1. **Remove disposable templates** — Templates that have no dewiki equivalent
   (like `{{Short description}}`, `{{Use mdy dates}}`). Remove them entirely,
   including their parameters.

2. **Convert template names** — Simple 1:1 replacements (`{{Steady}}` → `{{Unverändert}}`),
   infobox names (`Infobox company` → `Infobox Unternehmen`), hatnotes, sister projects.

3. **Convert citation templates** — `{{cite web}}`, `{{cite news}}` etc. become
   `{{Internetquelle}}`. `{{cite book}}` becomes `{{Literatur}}`. Convert all
   parameters according to the mappings. Remove parameters listed under `remove_params`.
   Add `|sprache=en` for English-language sources.

4. **Convert special templates** — Templates that need structural changes, not just
   renaming: `{{abbr}}` (extract first param), `{{URL}}` (convert to external link),
   `{{Unbulleted list}}` (join with `<br>`), `{{hlist}}` (join with comma).

5. **Convert section headers** — `== History ==` → `== Geschichte ==` etc.

6. **Convert namespaces** — `[[Category:` → `[[Kategorie:`, `[[File:` → `[[Datei:` etc.

7. **Convert image parameters** — `thumb` → `mini`, `right` → `rechts` etc.

8. **Convert magic words** — `DEFAULTSORT` → `SORTIERUNG`, `DISPLAYTITLE` → `SEITENTITEL`.

9. **Convert number formats** — Swap decimal separators (`.` ↔ `,`) and thousands
   separators (`,` ↔ `.`). Handle scale words (`billion` → `Milliarde`, `trillion` →
   `Billion` — these are false friends!).

10. **Convert date formats** — MDY → DMY (`December 3, 2019` → `3. Dezember 2019`),
    translate month names. Convert `As of` → `Stand`.

11. **Convert wikilinks** — Adjust known article title differences. For links where
    the German title is uncertain, leave as-is and flag with an inline comment
    `<!-- TODO: dewiki-Linkziel prüfen -->`.

12. **Convert table syntax** — Add `tabelle-zaehler` class where appropriate, adjust
    status templates (`Active` → `Aktiv`).

13. **Convert typography** — Quotation marks (`"..."` → `„..."`), dashes
    (em dash `—` → en dash `–`), non-breaking spaces before units (`10&nbsp;km`).

### Step 3: Translate prose (if requested)

After syntax conversion, translate the readable text if the user wants a full conversion.
Keep all wikitext syntax intact — links, templates, ref tags, HTML. Only translate the
human-readable prose, captions, and alt text.

Translation guidelines:
- Natural, encyclopedic German (or English for de→en)
- Preserve inline citations exactly where they are
- Keep proper nouns, brand names, and titles in the original language
- For quotes: provide both original and translation using `{{Zitat|Original|Übersetzung=...}}`
- Passive constructions and nominal style are typical for dewiki

### Step 4: Validate the output

Before presenting the result, check:
- Balanced braces: every `{{` has a matching `}}`
- Balanced ref tags: every `<ref>` has a `</ref>` (or is self-closing `<ref ... />`)
- No English template names remain (search for `cite web`, `cite news`, `Infobox company` etc.)
- No English namespace prefixes remain (`Category:`, `File:`)
- URLs are untouched (no number format changes inside URLs)
- ISO dates in citation parameters are untouched (don't convert `2024-01-15` to `2024,01,15`)

Flag anything uncertain with `<!-- TODO: ... -->` comments so the user can review.

## Number Format Conversion — Important Caveats

Number format swapping is the most error-prone part of conversion. These contexts
must be excluded from number format changes:

- **URLs**: anything after `://` until the next whitespace
- **ISO dates**: patterns like `2024-01-15` in citation date parameters
- **Version numbers**: `Python 3.12`, `iOS 17.4`
- **Template parameter values for `url=`, `abruf=`, `datum=`**
- **DOIs, ISBNs, ISSNs**: these have fixed formats

Only convert numbers that appear in prose text, table cells, or template parameters
where the value is genuinely numeric (like `Umsatz`, `Mitarbeiterzahl`).

## Adding New Rules

When encountering a template or pattern not covered by `rules.yaml`:

1. Read the current rules file to confirm it's missing
2. Determine the correct dewiki equivalent (check dewiki directly if possible)
3. Add the rule to the appropriate section in `rules.yaml`
4. Apply it to the current conversion
5. Add a comment with the date if the mapping is non-obvious

Rule categories in the YAML:
- `templates.simple` — 1:1 template name replacements
- `templates.remove` — templates to delete entirely
- `templates.infoboxes` — infobox name mappings
- `cite_templates` — which cite templates map to which German template
- `cite_params` — citation parameter name mappings
- `link_mappings` — known article title differences between wikis
- `section_headers` — section heading translations
- `special_templates` — templates needing structural transformation
- All other sections — see YAML file for full list

## Reverse Direction (de→en)

For de→en conversion, apply all rules in reverse: swap keys and values. The same
YAML file serves both directions. Pay attention to:
- `{{Internetquelle}}` → `{{cite web}}` (reverse the parameter mappings too)
- German number format → English number format
- DMY dates → MDY dates
- `[[Kategorie:` → `[[Category:` etc.

## Examples

### Citation conversion (en→de)

```
Input:  {{cite web |url=https://example.com |title=Test |publisher=BBC |access-date=January 5, 2024}}
Output: {{Internetquelle |url=https://example.com |titel=Test |hrsg=BBC |abruf=2024-01-05 |sprache=en}}
```

### Section header + number format

```
Input:  == History ==
        The company reported revenue of $1,234.56 million.
Output: == Geschichte ==
        Das Unternehmen meldete einen Umsatz von 1.234,56 Millionen US-Dollar.
```

### Special template

```
Input:  {{hlist|Rock|Pop|Electronic}}
Output: Rock, Pop, Electronic
```
