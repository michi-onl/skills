### 8. Karteikarten ("Flashcards" / "Lernkarten")

When the user wants flashcards / Frage-Antwort-Karten from slides, scripts, or a pasted text block.

**Trigger phrases:** "Karteikarten", "Lernkarten", "Flashcards", "Karten erstellen", "Frage-Antwort", "Leitner", "mach mir Karten aus".

#### Spaced-repetition reality (read first)

The student does not maintain a Leitner box or Anki schedule across days. Do **not** instruct them to set one up and do not assume cards will be reviewed later. Treat flashcards as an **in-session active-recall drill**: the realistic use is sitting down once and going through the deck now. The widget below approximates Leitner *within the session* (unknown cards get re-queued) without any persistence.

#### Generation rules (atomicity is mandatory)

1. **Atomarität:** One card = one question + one answer. No nested questions, no fact lists crammed onto one card. If a slide contains five facts, that is five cards, not one.
2. **Selbsterklärend:** The front must be answerable without the surrounding text. Not "Was ist das?" but "Was ist die Definition von [Begriff]?". Name the concept on the front.
3. **Strikte Trennung:** Front = question only. Back = short, exact answer only. No preamble, no filler, no pleasantries on either side.
4. **Kein Ballast:** No introductions or explanations outside the cards.

#### Three levels — recall alone is forbidden

A deck of only Wissen cards reinforces the student's known weakness (transfer failure despite recall mastery). Every deck mixes levels, even when the user only said "Karteikarten":

- **Wissen (~50%):** Definitions, terms, formulas, paragraphs. Atomic recall.
- **Anwendung (~30%):** Front states a short concrete scenario; back gives the concept/instrument that applies. Still one question, one answer.
- **Transfer (~20%):** Front poses a single combine/contrast/decide question ("Wann X statt Y — ein entscheidendes Kriterium?"); back gives one crisp criterion or comparison. Keep it atomic: one Transfer idea per card, not an essay.

For semester-spanning modules (see SKILL.md table), include at least one card connecting both semesters' content.

#### Lückencheck

Same obligation as the summary workflow: after the deck, list curriculum topics that appear missing from the source and ask whether they were skipped. Never omit this.

#### Output format

Default: **interactive HTML drill widget** via `show_widget` (call `read_me` with `["interactive"]` first).

On request ("als Text", "für Anki", "zum Exportieren"): output plain Markdown instead, one card per block, front and back strictly separated, in the format the user specified. No widget in that case.

#### Widget structure

```
Header: Modul/Thema + card count + level legend (Wissen / Anwendung / Transfer pills)
Card stack (one visible at a time):
  ├── Level badge (semantic color: Wissen=purple, Anwendung=blue, Transfer=amber)
  ├── Front (question) — large, centered
  ├── "Umdrehen" button → reveals back (answer) in place
  └── After flip: two self-grade buttons "Gewusst" / "Nochmal"
Footer: progress (n / total), "Nochmal"-queue count, restart button
```

#### Self-grading behavior (in-session Leitner)

- "Gewusst" → card removed from the round, advance.
- "Nochmal" → card pushed to the end of the current queue, reappears later this session.
- Round ends when the queue is empty. Show a short summary: how many needed a second pass (these are the exam-risk cards). Offer a restart that drills only the "Nochmal" cards.
- State is session-only. **Do not use `localStorage`.**

#### Styling

Follow the same CSS-variable and badge conventions as `visual-design-rules.md`. No emoji inside the widget. No colored outer background. Explanatory prose goes in the response text, not inside the widget.
