---
name: localization-translator
description: English to German translator for software localization files. Supports TOML, XLIFF, JSON, PO/POT (gettext), Properties, Android XML (strings.xml), iOS Strings, YAML, ARB (Flutter), PHP arrays, FTL (Fluent), and similar formats. Use when the user (1) uploads or pastes localization file content for translation, (2) asks to review existing German translations for user-friendliness, (3) requests improvements to translated UI strings, or (4) uses phrases like "übersetze", "lokalisiere", "prüfe auf Benutzerfreundlichkeit".
---

# Localization Translator (EN → DE)

Translate and review software localization files from English to German with focus on user-friendliness and accuracy.

## Supported Formats

TOML, XLIFF, JSON, PO/POT, Java Properties, Android XML, iOS .strings, YAML, ARB, PHP arrays, INI, CSV (key-value), Markdown with frontmatter, FTL (Fluent).

Preserve all syntax, keys, placeholders (`{name}`, `%s`, `%1$s`, `{{var}}`), and markup exactly.

## Pre-Translation Steps

Before any translation or review work, complete these steps in order.

### 1. Glossar-Abgleich

Check for terminology sources:
1. Check whether `references/glossary.md` exists in the skill directory. If yes, load it and treat its terms as default choices.
2. Ask the user whether a project-specific glossary exists (Crowdin, Pontoon, Weblate, Transifex, etc.). If yes, request it and treat project glossary terms as binding over the skill glossary.
3. If no glossary is available, note this explicitly and proceed. Do not silently invent terminology without acknowledging the absence.

When a translation decision conflicts with the glossary, do not silently override. Flag it as a glossary change proposal in the change table.

### 2. Register bestimmen (du/Sie)

Determine from context:
- **Informal (du)**: Browser extensions, gaming, social apps, dev tools, casual apps
- **Professional-informal (du, aber sachlich)**: Productivity tools, SaaS platforms (Slack, Notion, Figma) — du-Anrede, aber professioneller Ton ohne Slang
- **Formal (Sie)**: Banking, government, enterprise software, legal, healthcare

If unclear, ask the user or match existing translations in the file. Document the register decision explicitly.

### 3. Analyse

Before generating any output:
1. Scan all files for untranslated, identical-to-source, or empty strings
2. Scan for register inconsistencies (du/Sie, including capitalized "Du" at sentence starts)
3. Check placeholder parity between source and target
4. Check for terminology inconsistencies across all files
5. List findings as annotations before translating

## Translation Guidelines

### Technical Terms

Decide case-by-case. See `references/glossary.md` for common patterns. General rules:
- Keep established loanwords: Tab, Browser, App, Link, Button, Dropdown, Slider, Toggle
- Translate when natural German exists: Settings → Einstellungen, Download → Herunterladen, Save → Speichern
- Keep product names, brand terms, and code identifiers unchanged

### User-Friendliness Priorities

1. **Clarity**: Avoid ambiguity, use precise verbs
2. **Conciseness**: Shorter is better for UI elements
3. **Consistency**: Same term for same concept throughout
4. **Natural phrasing**: Read it aloud — does it sound like something a German would say?
5. **Action-oriented**: Use imperative for buttons/actions ("Speichern" not "Speichern Sie")

### Text Length & UI Constraints

German translations are typically 20–30% longer than English. Apply these strategies:

1. **Buttons/Menu items**: Keep as short as possible. Use infinitive verbs ("Speichern", "Löschen"), avoid auxiliary constructions
2. **Tooltips/Labels**: Aim for ≤ 150% of English length. Drop articles where natural ("Datei öffnen" not "Die Datei öffnen")
3. **Notifications/Messages**: Full sentences are fine, but avoid filler words ("bitte" only where genuinely polite, not as padding)
4. **Hard character limits**: If the format or context specifies a max length, prioritize meaning over completeness. Use standard abbreviations (z. B., Nr., Std.) or shorter synonyms
5. **Never truncate with "…"** unless the original English does the same

When in doubt, check if a shorter synonym exists in the glossary before adding words.

### Ambiguous & Context-Free Strings

Many localization files contain isolated strings without context. Handle them as follows:

1. **Check for comments**: Look for translator comments in the file (`# TRANSLATORS:`, `/* comment */`, `description` fields in ARB/XLIFF)
2. **Infer from key name**: `btn_open` → verb (Öffnen), `status_open` → adjective (Offen), `title_open` → could be either — flag it
3. **Common ambiguities to watch for**:
   - "Open" → Öffnen (verb) / Offen (adjective/state)
   - "Save" → Speichern (verb) / Gespeichert (state)
   - "Share" → Teilen (verb) / Freigabe (noun)
   - "View" → Anzeigen (verb) / Ansicht (noun)
   - "Post" → Posten/Veröffentlichen (verb) / Beitrag (noun)
   - "Set" → Festlegen (verb) / Satz/Gruppe (noun)
   - "Match" → Übereinstimmung (noun) / Übereinstimmen (verb)
   - "Report" → Melden (verb) / Bericht (noun)
4. **When truly ambiguous**: Translate with the most likely meaning (usually verb for UI actions) and add a comment in the change table noting the ambiguity
5. **Ask the user** if multiple strings are ambiguous and the wrong guess would cause user-facing issues

### Decision Protocol for Judgment Calls

Some strings require judgment calls that could reasonably go either way. These must be flagged as open questions in the change table, not decided silently.

Categories that require flagging:
- **Taglines and marketing copy** (not UI strings — they need adaptation, not translation)
- **Emoji additions or removals** compared to the source
- **Labels added by translators** that don't exist in the source language
- **Terminology where the glossary is silent** and multiple valid options exist
- **Feature flags** like "(experimentell)" that may have been intentionally added

Mark these in the change table with `⚠️ Rückfrage` and present options to the user.

### Plurals & ICU MessageFormat

German has two plural categories: `one` and `other`. Always verify that plural forms are correctly handled.

**ICU MessageFormat** (common in JS, Flutter, React):
```
{count, plural, one {# Element} other {# Elemente}}
{count, plural, one {Eine Datei ausgewählt} other {# Dateien ausgewählt}}
```

**Key rules**:
- German uses `one` (exactly 1) and `other` (everything else, including 0)
- Never add `zero`, `two`, `few`, `many` categories for German — they are not grammatically needed
- Watch for gender: `{count, plural, one {# neuer Tab} other {# neue Tabs}}` — adjective endings change
- Preserve the `#` symbol as the count placeholder inside plural blocks
- If the source has `=0` for a special zero case, keep it: `{count, plural, =0 {Keine Dateien} one {# Datei} other {# Dateien}}`

**PO/POT (gettext)**:
```po
msgid "%d file"
msgid_plural "%d files"
msgstr[0] "%d Datei"
msgstr[1] "%d Dateien"
```
- `Plural-Forms: nplurals=2; plural=(n != 1);` for German
- `msgstr[0]` = singular (n=1), `msgstr[1]` = plural (n≠1)

**Android XML**:
```xml
<plurals name="files_count">
    <item quantity="one">%d Datei</item>
    <item quantity="other">%d Dateien</item>
</plurals>
```

**iOS Stringsdict**: Use `NSStringLocalizedFormatKey` with `one` and `other` rules.

**String concatenation warning**: If a source string is clearly part of a concatenated sentence (e.g., `"You have "` + count + `" items"`), flag this to the user — German word order often requires restructuring the entire sentence, which isn't possible with concatenation.

## Format-Specific Notes

### XLIFF (.xliff, .xlf)
- Translate only `<target>` elements (or create them from `<source>` if missing)
- Set `state="translated"` on completed `<trans-unit>` entries; use `state="needs-review"` when uncertain
- Preserve `<note>` elements — they contain translator context
- Keep `id`, `resname`, and structural attributes unchanged

### PO/POT (gettext)
- Translate `msgstr` (leave `msgid` untouched)
- Keep `msgctxt` — it distinguishes identical English strings with different meanings
- Remove `#, fuzzy` flag only when the translation is verified correct
- Preserve all `#.` (extracted comments) and `#:` (source references)
- Set header `Content-Type: text/plain; charset=UTF-8` and `Plural-Forms: nplurals=2; plural=(n != 1);`

### Android XML (strings.xml)
- Skip strings with `translatable="false"`
- Use `<plurals>` for quantity strings (see Plurals section)
- Escape apostrophes: `It\'s` or wrap in `"It's"`
- Preserve `<xliff:g>` tags around untranslatable content (names, numbers)

### iOS .strings / Stringsdict
- Format: `"key" = "value";` — keep keys, translate values only
- Use `.stringsdict` files for plurals (not inline logic)
- `%@` (string), `%d` (integer), `%f` (float) — preserve all format specifiers

### ARB (Flutter)
- `@key` metadata entries contain descriptions and placeholders — preserve them, do not translate
- Plural/gender ICU patterns go directly in the value string
- Keep `@@locale` set to `"de"` in the translated file

### JSON (i18next, react-intl, etc.)
- Preserve nesting structure and key names exactly
- For i18next: `_plural` suffix keys or `{{count}}`-based plurals
- For react-intl/FormatJS: ICU MessageFormat syntax in values

### YAML
- Respect indentation strictly (YAML is whitespace-sensitive)
- Quote strings containing special YAML characters (`:`, `#`, `{`, `}`)
- For Rails i18n: top-level key should be `de:`

### FTL (Fluent)
- Translate only values, not message identifiers or attribute names
- Preserve `.label`, `.accesskey`, `.title` attribute structure
- Preserve placeables (`{ $variable }`, `{ -brand-name }`) exactly
- Preserve select expressions (`{ $count -> [one] ... *[other] ... }`)
- Respect `.accesskey` conventions (single character, should match a letter in the corresponding `.label`)

## Workflow

### New Translation

1. Complete Pre-Translation Steps (glossar, register, analyse)
2. Identify file format and preserve syntax
3. Check for format-specific requirements (see Format-Specific Notes)
4. Translate all user-facing strings
5. Handle plurals according to format conventions
6. Keep keys, placeholders, comments unchanged
7. Run QA (see below)
8. Output (see Output Format)
9. Append change table with all translated keys

### Partial Completion

When a file is already partially translated:

1. Complete Pre-Translation Steps
2. Identify untranslated strings (empty `msgstr`, missing `<target>`, English text in target fields)
3. Translate only the missing strings
4. Do **not** modify existing translations unless they contain obvious errors
5. Match register, terminology, and style of existing translations for consistency
6. Run QA
7. Output with change table listing newly translated keys

### Review/Correction

1. Complete Pre-Translation Steps
2. Identify issues: awkward phrasing, inconsistencies, overly literal translations, wrong register
3. **Change threshold**: If more than ~30% of strings would change, pause and ask the user whether they want error-only corrections or a full stylistic overhaul. Do not silently turn a review into a rewrite.
4. Apply corrections
5. Run QA
6. Output with change table

### Change Table (mandatory for all workflows)

Every workflow that modifies strings must append a change table. No exceptions.

| Wo (Schlüssel) | Was (vorher → nachher) | Warum |
|----------------|------------------------|-------|
| `welcome_msg` | Willkommen bei der App → Willkommen in der App | Natürlichere Präposition |
| `save_btn` | Abspeichern → Speichern | Kürzer, gängiger |
| `tagline` | ⚠️ Rückfrage: „Skizzieren. Teilen. Fertig." oder „Diagramme. Schnell. Klar." | Marketing-String, mehrere Optionen |

### Multi-File Projects

When processing multiple files:
- Do **not** output files with zero changes. List them as "keine Änderungen" and skip.
- Provide a per-file change table, not one giant table.
- Check register and terminology consistency across all files, not just within each file.

## QA

Run the QA script at `scripts/qa_check.py` or perform equivalent checks programmatically before outputting the final result. The checks cover:

- Placeholder parity (all placeholders from source present in target)
- Tag parity (HTML/XML tags preserved)
- Register consistency (du/Sie scan, including capitalized "Du" edge cases)
- Length ratio for short strings (buttons/labels ≤ 150% of English length, flagged if exceeded)
- Format syntax validation (JSON parse, XML parse, FTL parse as appropriate)
- Empty strings, double spaces, trailing whitespace
- Plural form correctness (two forms for German: one/other)
- Terminology consistency (same English term → same German term)
- Key names and structural syntax unchanged

If any issues are found, fix them before output and note them in the change table. Do not print the full QA checklist unless issues are found.

## File Writing Safety

When writing output files programmatically:
- Always write to a temporary file first, then rename (`os.rename`) to the target path
- Never open the target file in `'w'` mode and then run code that might fail before writing completes
- This prevents data loss from interrupted writes

## Output Format

- **Default (small files, <100 strings)**: Display in chat as code block with appropriate language tag (`toml`, `xml`, `json`, `yaml`, `properties`, `po`, `ftl`, etc.)
- **Large files (≥100 strings)**: Generate a structured diff. Either:
  - A JSON object containing only the changed keys with old and new values
  - A Python patch script that applies `str_replace`-style operations
  - The choice depends on format. JSON locale files → JSON diff. FTL/PO/Properties → patch script.
- **On request** ("als Datei", "zum Herunterladen"): Create downloadable file
- **Always**: Append the change table after the output. No exceptions.

Always use appropriate code fence language: `toml`, `xml`, `json`, `yaml`, `properties`, `po`, `ftl`, etc.
