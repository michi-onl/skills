---
name: localization-translator
description: English to German translator for software localization files. Supports TOML, XLIFF, JSON, PO/POT (gettext), Properties, Android XML (strings.xml), iOS Strings, YAML, ARB (Flutter), PHP arrays, and similar formats. Use when the user (1) uploads or pastes localization file content for translation, (2) asks to review existing German translations for user-friendliness, (3) requests improvements to translated UI strings, or (4) uses phrases like "übersetze", "lokalisiere", "prüfe auf Benutzerfreundlichkeit".
---

# Localization Translator (EN → DE)

Translate and review software localization files from English to German with focus on user-friendliness and accuracy.

## Supported Formats

TOML, XLIFF, JSON, PO/POT, Java Properties, Android XML, iOS .strings, YAML, ARB, PHP arrays, INI, CSV (key-value), Markdown with frontmatter.

Preserve all syntax, keys, placeholders (`{name}`, `%s`, `%1$s`, `{{var}}`), and markup exactly.

## Translation Guidelines

### Register (du/Sie)

Determine from context:
- **Informal (du)**: Browser extensions, gaming, social apps, dev tools, casual apps
- **Professional-informal (du, aber sachlich)**: Productivity tools, SaaS platforms (Slack, Notion, Figma) — du-Anrede, aber professioneller Ton ohne Slang
- **Formal (Sie)**: Banking, government, enterprise software, legal, healthcare

If unclear, ask the user or match existing translations in the file.

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

## Workflow

### New Translation

1. Identify file format and preserve syntax
2. Check for format-specific requirements (see Format-Specific Notes)
3. Translate all user-facing strings
4. Handle plurals according to format conventions
5. Keep keys, placeholders, comments unchanged
6. Run QA checklist (see below)
7. Output complete file content in chat (code block with appropriate language tag)

### Partial Completion

When a file is already partially translated:

1. Identify untranslated strings (empty `msgstr`, missing `<target>`, English text in target fields)
2. Translate only the missing strings
3. Do **not** modify existing translations unless they contain obvious errors
4. Match register, terminology, and style of existing translations for consistency
5. Run QA checklist
6. Output complete file with both existing and new translations
7. Append a list of newly translated keys

### Review/Correction

1. Identify issues: awkward phrasing, inconsistencies, overly literal translations, wrong register
2. Apply corrections
3. Run QA checklist
4. Output corrected file content
5. Append change table:

| Wo (Schlüssel) | Was (vorher → nachher) | Warum |
|----------------|------------------------|-------|
| `welcome_msg` | Willkommen bei der App → Willkommen in der App | Natürlichere Präposition |
| `save_btn` | Abspeichern → Speichern | Kürzer, gängiger |

### QA Checklist

Run through this checklist before outputting the final result. Do not print the checklist unless issues are found — just silently verify.

- [ ] All placeholders (`{name}`, `%s`, `%1$s`, `{{var}}`, `#`) preserved and unmodified
- [ ] Consistent register (du/Sie) throughout the entire file
- [ ] No broken HTML/XML tags or markup
- [ ] Special characters correctly escaped for the file format
- [ ] Text length acceptable for UI elements (buttons ≤ ~150% of English)
- [ ] No double spaces, missing punctuation, or trailing whitespace
- [ ] Plural forms correct (two forms for German: one/other)
- [ ] Same English term consistently translated with the same German term
- [ ] Key names and structural syntax unchanged
- [ ] No untranslated strings left (unless intentionally skipped, e.g. `translatable="false"`)

If any issues are found, fix them before output and note them in the change table.

## Output Format

- **Default**: Display in chat as code block
- **For large locale files**: Generate a Python patch file that applies the specified changes.
- **On request** ("als Datei", "zum Herunterladen"): Create downloadable file

Always use appropriate code fence language: `toml`, `xml`, `json`, `yaml`, `properties`, `po`, etc.
