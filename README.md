# Claude Code Skills

A collection of custom skills for [Claude Code](https://claude.ai/code).

## Skills

### commons-upload

Evaluates, curates, and uploads images to Wikimedia Commons. A 10-step pipeline covering technical vetting, visual review, deduplication, metadata handling, description generation, and automated upload via Pywikibot.

### localization-translator

Translates software localization files from English to German. Supports TOML, JSON, XLIFF, PO/POT, Android XML, iOS Strings, YAML, ARB, PHP arrays, and other common formats. Preserves formatting and maintains register consistency.

### skill-creator

A meta-skill for building, testing, and iterating on new skills. Covers the full development loop from capturing intent through writing drafts, running evals, grading outputs, and optimizing skill trigger descriptions.

### wende-spotify-list

Automates the monthly update of the German Wikipedia article "Liste der meistgestreamten Künstler auf Spotify". Fetches current data from the English source article, converts wikitext conventions, and runs quality checks via Python scripts.

### wende

Converts Wikipedia wikitext syntax between English and German Wikipedia conventions. Handles templates, citations, formatting, numbers, and dates through rule-based transformations. No editorial changes, just mechanical syntax conversion.

### wiki-artikel

Creates complete German Wikipedia articles from English wikitext sources. Goes beyond syntax conversion to produce independent, encyclopedic articles following dewiki editorial standards and structure conventions.

## Structure

Each skill lives in its own directory and follows a common layout:

- `SKILL.md` — the skill definition and workflow
- `references/` — glossaries, templates, rules
- `scripts/` — automation scripts (where applicable)

## Installation

Clone this repo into your Claude Code skills directory:

```
git clone https://github.com/michi-onl/skills.git ~/.claude/skills
```
