---
name: translating-localization-files
description: >
  Use when the user wants to translate software localization files from English to
  German, or to review/improve existing German UI strings for user-friendliness.
  Supports TOML, XLIFF, JSON, PO/POT (gettext), Properties, Android XML (strings.xml),
  iOS .strings, YAML, ARB (Flutter), PHP arrays, FTL (Fluent). Triggers: pasted or
  uploaded localization content, "übersetze", "lokalisiere",
  "prüfe auf Benutzerfreundlichkeit".
---

# Localization Translator (EN → DE)

Translate and review software localization files from English to German with focus on user-friendliness and accuracy.

## Supported Formats

TOML, XLIFF, JSON, PO/POT, Java Properties, Android XML, iOS .strings, Xcode String Catalog (.xcstrings), WebExtension messages.json (chrome.i18n), YAML, ARB, PHP arrays, INI, CSV (key-value), Markdown with frontmatter, FTL (Fluent).

Preserve all syntax, keys, placeholders (`{name}`, `%s`, `%1$s`, `%0`, `{{var}}`, `$NUMBER`), and markup exactly.

## Input Handling

First detect which surface you are on, then pick the entry point:

- **Claude.ai (chat sandbox)** — files arrive as uploads. Run `find /mnt/user-data/uploads -type f` first. If that directory exists and has files, that is the source. Large multi-file uploads (10+ files) sometimes land as an empty-looking directory or as a single archive — do not assume a file is missing until this returns nothing.
- **Claude Code (real filesystem)** — there is no `/mnt/user-data/uploads`. Operate on the repository working tree instead: use the path the user gives, or the current working directory, and locate locale files (`_locales/`, `*.xcstrings`, `*.strings`, `locales/`, `i18n/`, `*.po`) within it. Edit files in place and surface results as a `git diff` / commit rather than chat output.

Then, on either surface:

1. If a `.zip`/`.tar.gz` is provided, extract it to a working directory first, then operate on the extracted tree. Bundling many locale files as one archive is the reliable path for big uploads — suggest it if individual uploads fail to appear.
2. Match source and target files by locale (`en` ↔ `de`, `en-US` ↔ `de-DE`, `_locales/en/messages.json` ↔ `_locales/de/messages.json`). For bilingual single-file formats (`.xcstrings`, `.po`), source and target live in the same file.

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
5. **Match the source's truncation convention** — add "…" only when the English source already truncates

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

### WebExtension messages.json (chrome.i18n)

Browser-extension format: each key maps to an object, not a bare string.

```json
"greeting": { "message": "Hello $USER$", "description": "...", "placeholders": { "user": { "content": "$1" } } }
```

- Translate **only** the `message` value. Never touch `description` (translator note) or `placeholders` (binding map).
- `$USER$`-style named placeholders inside `message` are defined in `placeholders` — preserve them verbatim, including case.
- When running QA, this file is named `messages.json` and auto-detects correctly; if you renamed it, pass `--format messages` so `description` fields are not mistaken for translatable strings.

### Xcode String Catalog (.xcstrings)

Modern Apple format (Xcode 15+), replacing `.strings`/`.stringsdict`. JSON structure, bilingual in one file.

- The translatable text is at `strings.<key>.localizations.<lang>.stringUnit.value`. Add or edit the `de` localization; leave the source language (usually `en`) untouched.
- Set `stringUnit.state` to `"translated"` when done, `"needs_review"` when uncertain. Do not leave it `"new"`.
- Skip entries marked `"shouldTranslate" : false`.
- Plurals/device variations live under `variations.plural.<one|other>.stringUnit.value` — fill both German categories.
- The `%@`, `%lld`, `%1$@` format specifiers and `%#@var@` substitution tokens must be preserved exactly.
- QA: pass the single `.xcstrings` file as both source and target — the QA script splits source vs. `de` internally.

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
4. Leave existing translations unchanged (correct only obvious errors)
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

#### Machine-translated drafts

The common real case is reviewing a file that was pre-filled by machine translation (e.g. Gemma, DeepL, Google), not a hand-made translation.

- Treat existing target values as a **draft, not ground truth** — MT output is often literal, picks the wrong sense of ambiguous words, or breaks placeholders. Verify against the source rather than trusting the German.
- Strip MT tool artifacts and machine-translation marker comments (e.g. `translategemma`, `# auto-translated`) from the output.
- MT frequently mixes register (du/Sie) within one file — a full register pass is usually warranted here even if individual strings look fine.

### Change Table (mandatory for all workflows)

Every workflow that modifies strings must append a change table. No exceptions.

| Wo (Schlüssel) | Was (vorher → nachher)                                                       | Warum                              |
| -------------- | ---------------------------------------------------------------------------- | ---------------------------------- |
| `welcome_msg`  | Willkommen bei der App → Willkommen in der App                               | Natürlichere Präposition           |
| `save_btn`     | Abspeichern → Speichern                                                      | Kürzer, gängiger                   |
| `tagline`      | ⚠️ Rückfrage: „Skizzieren. Teilen. Fertig." oder „Diagramme. Schnell. Klar." | Marketing-String, mehrere Optionen |

### Multi-File Projects

When processing multiple files:

- Do **not** output files with zero changes. List them as "keine Änderungen" and skip.
- Provide a per-file change table, not one giant table.
- Check register and terminology consistency across all files, not just within each file.

## QA

Run the QA script at `scripts/qa_check.py` before outputting the final result. It loads and compares source/target for these formats: `json`, WebExtension `messages`, `ftl`, `properties`, iOS/macOS `strings`, `xcstrings`, Android `androidxml`, and `po`. Format auto-detects from the target extension; override with `--format`. For other formats (XLIFF, YAML, ARB, TOML) perform the equivalent checks programmatically.

```
python scripts/qa_check.py <source> <target> [--format FMT] [--register du|sie|none]
```

The checks cover:

- Placeholder parity (all placeholders from source present in target, incl. `%0`/`%1` positional and `$NUMBER` styles)
- Tag parity (HTML/XML tags preserved)
- Register consistency (du/Sie scan, including capitalized "Du" edge cases and informal `du/dein` leaking into Sie-mode)
- Length ratio for short strings (buttons/labels ≤ 150% of English length, flagged if exceeded)
- Empty strings, double spaces, leading/trailing whitespace
- Untranslated strings (target identical to source)
- Key parity (missing or extra keys between source and target)

If any issues are found, fix them before output and note them in the change table. Do not print the full QA checklist unless issues are found.

### Multi-locale & cross-variant QA

The placeholder, tag, key-parity, and whitespace checks are **language-independent**. Even when the translation task is EN→DE only, the same script can validate any target locale — useful for catching broken placeholders (`%0` written as `0%`, dropped `%1$s`, stray backticks) across a whole `_locales/` tree.

- For non-German locales, pass `--register none` to suppress the du/Sie check (which would otherwise produce noise).
- **en-US → en-GB / en-AU** is a localization task, not a translation. When asked to populate British or Australian English from US English, apply spelling transforms only (see `references/glossary.md` → "English variants"); do not paraphrase. Preserve `Mac`, `MAC`, `Wi-Fi`, and product names.

## File Writing Safety

When writing output files programmatically:

- Always write to a temporary file first, then rename (`os.rename`) to the target path
- Never open the target file in `'w'` mode and then run code that might fail before writing completes
- This prevents data loss from interrupted writes

## Output Format

Pick the output mode from the surface (see Input Handling):

**Claude Code (real filesystem):** Edit locale files in place. Do not print full file contents to chat. Surface the result as a `git diff` (or staged changes), run `qa_check.py` across the affected files, and append the change table. This is the default whenever you are operating on a working tree.

**Claude.ai (chat sandbox):**

- **Default (small files, <100 strings)**: Display in chat as code block with appropriate language tag (`toml`, `xml`, `json`, `yaml`, `properties`, `po`, `ftl`, etc.)
- **Large files (≥100 strings)**: Generate a structured diff. Either:
  - A JSON object containing only the changed keys with old and new values
  - A Python patch script that applies `str_replace`-style operations
  - The choice depends on format. JSON locale files → JSON diff. FTL/PO/Properties → patch script.
- **On request** ("als Datei", "zum Herunterladen"): Create downloadable file

**Always (both surfaces)**: Append the change table after the output. No exceptions.

Always use appropriate code fence language: `toml`, `xml`, `json`, `yaml`, `properties`, `po`, `ftl`, etc.
