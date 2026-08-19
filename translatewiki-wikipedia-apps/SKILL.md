---
name: translatewiki-wikipedia-apps
description: "German localization of the Wikipedia iOS/Android apps on translatewiki.net: new strings, outdated strings, QA sweeps. Trigger: \"translatewiki\", \"Wikipedia-App übersetzen\", \"QA-Lauf\"."
---

# Wikipedia apps → de on translatewiki.net

Works the `out-wikimedia-mobile-*` message groups (Wikipedia iOS + Android, ~3,900 German
strings) through the MediaWiki API. Three jobs: **translate new strings**, **update outdated
ones**, **QA what is already translated**.

For localization files in a repo (JSON, XLIFF, `.xcstrings`, …) use `translating-localization-files`
instead. This skill is only for the translatewiki workflow.

## The one rule

Nothing reaches the wiki without the user seeing it first. `pull` and `qa` are read-only, `push`
is a dry run unless `--confirm` is passed. Edits land publicly under the user's own translator
account, so the review step is what makes them the user's work rather than unattributed machine
output. Never pass `--confirm` in the same turn that produced the translations — show the change
table, wait for approval.

## Setup (once)

Credentials live in `~/.config/translatewiki/claude.json`, chmod 600:

```json
{"username": "Mike is Michi@claude-twn", "password": "<botpassword>"}
```

The user creates the BotPassword themselves at
<https://translatewiki.net/wiki/Special:BotPasswords> — grants **Basic rights**, **Edit existing
pages**, **Create, edit, and move pages**. Suggest they run it via `!` so the secret never passes
through a tool call. Verify with `twn.py auth`; it prints the account's groups and confirms the
`translate` right.

Reading needs no credentials at all — `status`, `pull` and `qa` work anonymously, so a whole
translation pass can be prepared before the login is ever set up.

## Commands

All examples assume `python3 ~/.claude/skills/translatewiki-wikipedia-apps/scripts/twn.py`.

| Command | Purpose |
| --- | --- |
| `status` | backlog counts per platform |
| `term --en "reading list" --de Leseliste` | how a term is used **per platform** — run before any terminology decision |
| `pull --filter new\|outdated\|todo --out batch.json` | fetch work, with English diffs and qqq docs |
| `sweep batch.json --replace 'alt=>neu'` | mechanical term substitution across a batch |
| `qa batch.json --only-new` | check proposed translations before pushing |
| `qa --filter done --fix-batch fix.json` | full sweep over live translations |
| `diff batch.json --out review.html` | **render the batch for proofreading** |
| `push batch.json` / `push batch.json --confirm` | dry run / save |

`--platform ios\|android\|all`, `--key REGEX` and `--limit N` narrow any of them.

## The review step

Every batch gets rendered before it is pushed — a change table in chat covers a dozen strings, not
a hundred:

```
twn.py diff /tmp/outdated.json --out /tmp/review.html --qqq
```

The page shows each message as a word-level diff (English `was`→`now` above, German
`current`→`new` below), with the note and any QA findings inline, and filter buttons for
*Geändert / Alle / Mit Notiz / Mit QA-Befund / Offen*. Hand the user the file path, or publish it
as an Artifact with `--fragment` for a link they can open anywhere. `--format md` gives the same
content as Markdown when a diff in the terminal is enough.

Read it yourself before handing it over — a word-level diff is where mechanical damage becomes
visible. The 2026-08-19 rename sweep produced exactly one broken compound
(„Leselistenansicht" → „Sammlungen­ansicht", correct is „Sammlungsansicht") out of 284 edits, and
nothing but the diff view would have surfaced it.

## Run A — new and outdated strings

```
twn.py status
twn.py pull --filter outdated --out /tmp/outdated.json
```

Each entry arrives with everything needed to decide:

```json
{
  "key": "wikipedia-android-strings-filter_hint_filter_my_lists_and_articles",
  "definition": "Filter my collections",
  "documentation": "Hint text for filtering the set of collections…",
  "current": "Meine Listen filtern",
  "english_was": "Filter my lists",
  "english_now": "Filter my collections",
  "new": "", "note": ""
}
```

Fill `new` for every entry you are confident about; leave it empty to skip that string. Put
anything the user must decide into `note` — skipping is always better than guessing.

**Outdated strings are a diff job, not a retranslation job.** `english_was` → `english_now` shows
exactly what changed upstream. Change only the part of the German that the English change affects
and keep the rest of the wording; these strings usually already carry a reviewed translation, and
rewriting them churns other people's work for nothing.

**Decide terminology once per run, not per string.** When the same source rename drives dozens of
fuzzy strings, group them, put the decision to the user once, then apply it to all of them.

Then check, report, and only then push:

```
twn.py qa /tmp/outdated.json --only-new
twn.py diff /tmp/outdated.json --out /tmp/review.html
twn.py push /tmp/outdated.json            # dry run, shows every edit
twn.py push /tmp/outdated.json --confirm  # after the user approves
```

Present the batch as a change table before asking for approval, and point at the review page for
the full set:

| Schlüssel | vorher → nachher | warum |
| --- | --- | --- |
| `filter_hint_filter_my_lists…` | Meine Listen filtern → Meine Sammlungen filtern | EN „lists" → „collections" |

## Terminology decisions

A term decision is never a per-string call and rarely a one-platform call. Before putting one to
the user, **measure it**:

```
twn.py term --en "reading list" --de Leseliste
```

It reports, per platform, how many source strings carry the English term, how many German strings
carry the German one, and — the part that matters — how many of each *lack* the counterpart. A
platform that shows up in one column but not the other has renamed while the other has not.

That check is not optional. On 2026-08-19 the *reading list* → *collection* rename looked like a
single 113-string Android job; `term` showed 60 iOS source strings still saying „reading list"
against 1 on Android. Following the rename on iOS therefore means **translating ahead of the
English source** — a legitimate choice, but one the user has to make knowingly, not a detail that
surfaces after the push.

Once the decision is made, three things follow, in order:

1. **Update `references/glossary.md`.** It is binding *and* it drives the QA checker — leave it
   stale and every string in the new terminology raises a glossary warning, which trains you to
   ignore the one warning that matters. Record the retired term, the replacement, the compound
   forms, and any literal that must not be swept.
2. **Sweep**, listing the longest form first so plurals are consumed before singulars, and
   shielding literals that only look like prose:

   ```
   twn.py sweep /tmp/batch.json \
     --replace 'Leselisten=>Sammlungen' --replace 'Leseliste=>Sammlung' \
     --replace 'Standardliste=>Standardsammlung' \
     --protect 'reading_lists[ _]export\.json' \
     --where-de Leseliste --note 'Rebrand 2026-08-19'
   ```

   `sweep` knows nothing about German morphology. It will happily produce „Sammlungenansicht" from
   „Leselistenansicht". That is expected — it is a first pass, not a result.
3. **Proofread the diff** and hand-fix the compounds. A useful scan afterwards:
   `grep -o 'NeuerTerm[a-zäöüß][a-zäöüß]*'` over the batch catches most fused compounds.

A rename also changes which strings need pushing at all: once the German text differs everywhere,
the unchanged-string problem below disappears, and previously untranslatable strings (an in-app
„X is now called Y" tooltip) become translatable.

## Run B — full QA sweep

```
twn.py qa --filter done --platform all --fix-batch /tmp/fix.json
```

Checks every live German string against its English source: placeholder parity, PLURAL arity,
markup and link counts, du/Sie register, glossary, typography, length, whitespace. Errors are
things that break the app or the string; warnings are judgment calls.

`--fix-batch` writes the flagged messages as a normal batch (with the findings in `note`) so
corrections flow through the same review-and-push path as Run A. Add `--errors-only` to limit it
to real breakage, `--json` for machine-readable output.

Triage the report rather than dumping it: hundreds of `length` warnings on long-form onboarding
copy are noise, whereas a dropped `<br>` or an `<a>` that lost its `href` is a real defect worth
fixing. Do not mass-correct warnings — every fix is a public edit to someone else's translation,
so fix defects and genuine register drift, and leave defensible stylistic choices alone.

## Translating these apps

`references/glossary.md` is binding and was derived from the strings already in the apps. Load it
before translating. The essentials:

- **Register: `du`, lowercase.** Capitalize `Du` only at the start of a sentence — including after
  `<b>` or `<br>`. Buttons stay in the infinitive („Speichern", not „Speichere").
- **Placeholders** are reproduced exactly. iOS uses `$1`-style tokens only and they may be
  reordered freely; Android uses `%s`/`%1$s`/`%d`. Bare Android `%s` is positional — if a string
  has more than one and German needs a different order, flag it instead of guessing.
- **PLURAL**: `{{PLURAL:$1|Singular|Plural}}` or `{{PLURAL|one=…|…}}`. German takes one or two
  grammatical forms — one is correct when the noun does not inflect (`{{PLURAL:$1|$1 Byte}}`).
  `0=`/`1=` arms are exact-value extras and do not count. Never add `zero`/`few`/`many`.
- **Markup** (`<a>`, `<b>`, `<br>`, `[[…]]`) survives unchanged, but `href` targets should point at
  the German Wikipedia where the English points at `en.wikipedia.org`.
- **Typography**: „…" quotes, `…` not `...`.
- Read the `documentation` (qqq) field before translating anything ambiguous — it is what
  disambiguates "Open" the verb from "Open" the state. When qqq is missing and the key does not
  settle it, leave `new` empty and ask.

## Gotchas

- `push` refuses any batch with QA **errors**. `--ignore-qa` exists but means the string is going
  in broken — get the user to say so explicitly.
- Edits are throttled to one per 2s (`--throttle`). Don't raise it; translatewiki is a small
  volunteer-run site.
- `push` writes `"pushed": true` back into the batch file **after every single edit**, so an
  interrupted run can be resumed with `push batch.json --confirm --resume`, which skips what
  already went out. The checkpoint is written even when the run dies mid-loop.
- **Never reconstruct push progress from the API.** `list=messagecollection` is a derived index
  and lags badly right after a burst of edits — on 2026-08-19 it reported 6 of 115 saved
  translations when all 115 were already live, which would have caused 109 redundant re-saves.
  The batch file's `pushed` flags are the authority; if you truly must check the wiki, wait several
  minutes, or fetch the individual pages rather than the collection.
- A dropped connection mid-push used to escape as a raw `RemoteDisconnected` traceback. `_call`
  now retries `http.client.HTTPException` and `OSError` alongside `URLError`, but a push that dies
  anyway leaves a valid checkpoint — resume, don't restart.
- Filter semantics: `todo` = new + outdated, `new` = never translated, `outdated` = fuzzy
  (translated, then the English changed), `done` = translated and not fuzzy.
- Saving a translation clears the fuzzy flag automatically. Any stray `!!FUZZY!!` marker is
  stripped before saving.
- **`push` skips entries whose `new` equals `current`.** That is the right default — it stops a
  batch from re-saving strings nobody touched — but it means a fuzzy string whose German the
  English change did not affect cannot be confirmed the normal way. Use
  `push batch.json --include-unchanged` to save those; on the wiki the stored text still carries
  the `!!FUZZY!!` marker, so re-saving the identical text is a real edit that clears it. The dry
  run labels those entries so they are not mistaken for content changes. Only do this when the
  German has genuinely been checked against the new English — it publicly asserts the translation
  is current.
- iOS and Android are separate groups with separate string sets — a term fixed in one is not fixed
  in the other, and **they rename concepts at different times**. `status` shows them apart and
  `term` shows the divergence.
- Tab and feature names usually already have an established German form somewhere in the translated
  set. Look it up (`pull --filter done --key '<prefix>'`, or `term --en "Home"`) instead of coining
  one: Home → **Start**, For You → **Für dich**, Explore → **Entdecken**, Community feed →
  **Community-Feed**.
- The default edit summary discloses AI assistance with human review. Override with `--summary`,
  but keep the disclosure honest.
