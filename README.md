# Claude Code Skills

A collection of custom skills for [Claude Code](https://claude.ai/code).

## Skills

### dhbw-study

Helps prepare for DHBW Wirtschaftsinformatik coursework and exams. Covers lecture prep, practice questions, cheat sheets, summarizing slides, analyzing past exams, and study plans.

### gutachtenstil

Solves German legal cases and exam questions in proper Gutachtenstil format. Covers BGB, Sachenrecht, and Schuldrecht with structured claim examinations.

### liquid-glass

Builds or restyles websites with a glassy, translucent, frosted, or Apple-style Liquid Glass look. Covers plain HTML/CSS/JS, Next.js, Zola, shadcn/ui, and Bootstrap.

### macos-file-sorter

Sorts, organizes, and cleans up files on macOS. Handles Downloads, Desktop, camera imports, design assets, and school documents with preview-before-move workflow.

### managing-divi-sites

Manages, styles, and audits WordPress sites built with the DIVI theme through the REST API. Fixes button styles, hover states, auth issues, and performance problems.

### planning-travel

Plans holidays, short trips, and travel adventures. Brainstorms destinations, builds itineraries, and checks practical details like visa requirements and best travel seasons. Tailored to the user's travel style and history.

### proxmox

Manages a single-node Proxmox VE server over SSH. Covers VM and LXC lifecycle, snapshots, backups, storage, monitoring, networking, and maintenance.

### skill-sync

Compares locally installed Claude skills against the canonical GitHub repo and packages updated `.skill` files for anything out of sync. Works on claude.ai, Claude Code, and OpenCode. The repo is the source of truth, so packaging pulls repo → local.

### translating-localization-files

Translates software localization files from English to German. Supports TOML, JSON, XLIFF, PO/POT, Android XML, iOS Strings, YAML, ARB, PHP arrays, and other common formats. Preserves formatting and maintains register consistency.

### translatewiki-wikipedia-apps

Localizes the Wikipedia iOS and Android apps into German on translatewiki.net. Translates new
strings, updates outdated ones against a diff of the English source, and runs full QA sweeps over
the existing translations. Read-only without credentials; every edit passes a review gate before
it is pushed.

### uploading-to-commons

Evaluates, curates, and uploads images to Wikimedia Commons. A 10-step pipeline covering technical vetting, visual review, deduplication, metadata handling, description generation, and automated upload via Pywikibot.

### wende

Converts Wikipedia wikitext syntax between English and German Wikipedia conventions. Handles templates, citations, formatting, numbers, and dates through rule-based transformations. No editorial changes, just mechanical syntax conversion.

### wende-spotify-list

Automates the monthly update of the German Wikipedia article "Liste der meistgestreamten Künstler auf Spotify". Fetches current data from the English source article, converts wikitext conventions, and runs quality checks via Python scripts.

### widget-st

Builds widgets for widget.st (WidgetStar) that actually render once installed. Covers the iframe and script embed contracts, autosizing, the `WS.settings` schema, and the dashboard fields, with a local harness and a validator that catch the invisible-widget failure before publishing.

### wiki-artikel

Creates complete German Wikipedia articles from English wikitext sources. Goes beyond syntax conversion to produce independent, encyclopedic articles following dewiki editorial standards and structure conventions.

## Structure

Each skill lives in its own directory and follows a common layout:

- `SKILL.md` — the skill definition and workflow
- `references/` — glossaries, templates, rules
- `scripts/` — automation scripts (where applicable)
- `assets/` — starter templates and boilerplate (where applicable)

## Installation

Clone this repo into your Claude Code skills directory:

```
git clone https://github.com/michi-onl/skills.git ~/.claude/skills
```
