# Glossar — Wikipedia-Apps (iOS/Android), de-DE

Terminology for the `out-wikimedia-mobile-*` groups on translatewiki.net. Every entry below was
derived from the ~3,800 German strings already in the apps (counts measured 2026-08-19), not
invented. The table is machine-read by `scripts/twn.py qa` — keep the pipe format intact.

**How the QA parser reads it:** column 1 is the English trigger, column 2 the expected German
(slash-separated alternatives, all accepted), column 3 free notes. A `⚠` anywhere in the notes
downgrades the check to info level — use it for terms where context legitimately varies.

## Kernbegriffe

A trailing `*` is a stem: `bearbeit*` matches Bearbeitung, bearbeitet and bearbeiten alike.

| English | Deutsch | Notes |
| --- | --- | --- |
| article | Artikel | 380/390 existing strings; never „Seite" for an article |
| reading list | Sammlung* | ⚠ EN-only legacy term; iOS source still says „reading list", de follows the rebrand (see below) |
| collection | Sammlung* | de follows the 2025 EN rename lists→collections, decided 2026-08-19; **Leseliste** is the retired term and should not reappear in new strings |
| watchlist | Beobachtungsliste* | 36/36 |
| talk page | Diskussionsseite* | 45/48 |
| edit summary | Zusammenfassung* | not „Bearbeitungszusammenfassung" in tight slots |
| edit history | Versionsgeschichte | ⚠ „edit"/„revision" history are the same thing in German |
| revision | Version* | not „Revision" |
| diff | Unterschied*/Versionsunterschied* | ⚠ „Diff" appears twice, avoid it in new strings |
| undo | rückgängig | „rückgängig machen" |
| rollback | zurücksetzen | admin action, distinct from undo |
| thank | dank*/bedank* | the Thanks extension |
| contribution | Beitr*/Bearbeitung* | 48/65 plural „Beiträge" |
| history | Verlauf/Versionsgeschichte | ⚠ **Verlauf** = the app's own browsing history; **Versionsgeschichte** = a page's revision history. Do not mix |
| saved | gespeichert | 73/78 |
| notification | Benachrichtigung* | 65/73 |
| settings | Einstellung* | |
| search | such*/Suchanfrage* | stem covers Suche, suchen, Suchverlauf, durchsuchen |
| explore | entdeck*/erkund* | ⚠ „Entdecken" for the feed tab; „erkunden" is fine in prose |
| feed | Feed | ⚠ „Startseite" in 10 older strings; prefer „Feed" |
| log out | abmelden | and „anmelden" for log in |
| account | Konto | not „Account" |
| username | Benutzername* | |
| category | Kategorie* | |
| namespace | Namensraum | |
| section | Abschnitt* | |
| lead section | Einleitung | |
| reference | Einzelnachweis*/Beleg* | ⚠ „Referenz" only for non-citation senses |
| image caption | Bildunterschrift* | the suggested-edits task; **not** „Bildbeschreibung" |
| short description | Kurzbeschreibung* | the Wikidata description |
| suggested edits | Vorgeschlagene Bearbeitungen | |
| patroller | Sichter*/Kontrolleur* | ⚠ context-dependent; check the qqq documentation |
| vandalism | Vandalismus | |
| donate | spenden/Spende* | |
| sync | synchron* | covers synchronisiert, Synchronisierung |
| tap | tipp* | ⚠ mobile gesture; „berühren" is drift, „klicken" is wrong |
| swipe | wisch* | |
| long press | gedrückt halten | |
| dark mode | dunkler Modus/Dunkelmodus | |
| font size | Schriftgröße | |
| on this day | An diesem Tag | the feed card and the game |
| featured article | Artikel des Tages | dewiki convention, not „Vorgestellter Artikel" |
| picture of the day | Bild des Tages | |
| top read | Meistgelesen | |
| in the news | In den Nachrichten | |
| randomizer | Zufallsartikel | |
| streak | Serie | games feature |

### Leseliste → Sammlung (Rebrand, 2026-08-19)

English renamed *reading list* → *collection* on Android in 2025; iOS has **not** followed yet and its
source strings still say „reading list". German follows the rebrand on both platforms by user
decision, so the German term is **Sammlung** even where the English source still reads „reading
list". Both nouns are feminine, so articles and adjective endings carry over unchanged.

| alt | neu |
| --- | --- |
| Leseliste / Leselisten | Sammlung / Sammlungen |
| Standardliste | Standardsammlung |
| Leselistenartikel | Artikel aus Sammlungen |
| Entdecken-Leseliste | Entdecken-Sammlung |

Do not translate the literal export filenames (`reading_lists export.json`,
`reading_lists_export.json`) — they are legacy identifiers, not prose.

## Register

**du, kleingeschrieben.** 239 lowercase `du` / 305 lowercase `dein*` against 19 genuinely formal
strings — the formal ones are drift in newer Android strings (`on_this_day_game_*`, `patroller_*`,
`talk_warn_*`) and should be corrected when touched, not left as precedent.

- „Deine Leselisten", not „Ihre Leselisten"
- Capitalize `Du` only at the start of a sentence — including after `<b>`, `<br>` and `</strong>`,
  which the QA check treats as sentence boundaries
- Buttons stay in the infinitive: „Speichern", „Teilen", „Abbrechen" — never „Speichere"

## Platzhalter

Measured across both apps:

| Platform | Styles in use | Count |
| --- | --- | --- |
| iOS | `$1`, `$2`, … only | 493 |
| Android | `%s`, `%1$s`, `%d`, `%1$d` | 385 |

- Reproduce every placeholder exactly, same count, same spelling.
- Android bare `%s`/`%d` are **positional** — if a German sentence needs a different order and the
  source has more than one bare placeholder, the string cannot be reordered safely. Flag it for an
  upstream request to switch to `%1$s` indices rather than guessing.
- iOS `$1` tokens can be reordered freely.

## PLURAL

Both syntaxes appear in these groups:

```
{{PLURAL:$1|$1 Artikel|$1 Artikel}}
{{PLURAL|one=%1$d Bearbeitung seit %2$s|%1$d Bearbeitungen seit %2$s}}
```

- German takes **exactly two** forms: singular and everything else (including 0).
- Never add `zero`/`few`/`many`. The QA check errors on any other arity.
- Keep the count placeholder inside both arms.
- Watch adjective and article endings across the two arms: „1 neuer Artikel" / „5 neue Artikel".

## Markup

`<a>`, `</a>`, `<b>`, `<br>`, `<br/>`, `<big>` and `[[…]]` appear in source strings. Tag set and
order must survive translation unchanged — the QA check compares them as sorted multisets.

## Typografie

- German quotes „…" — 100 strings already use them against 60 with straight quotes
- Ellipsis `…`, not `...`
- No space before `:`, `!`, `?`
- Non-breaking space in „z. B." and „5 km" where the string allows it
