### 7. Interactive Daily Learning Plan ("Lernplan" / "tägliche Prompts")

When the user asks for a structured day-by-day study plan with interactive prompts, or when a multi-week exam prep plan has been established and the user wants to work through it day by day.

**Trigger phrases:** "tägliche Prompts", "Lernplan erstellen", "interaktiver Lernplan", "Tag für Tag", "Woche 1 Prompts", "wie soll ich jeden Tag vorgehen", or when the user says they want to "abarbeiten" a study plan.

**Build the widget using `show_widget`** (call `read_me` with `["interactive"]` first). The widget must contain:

#### Required widget structure

```
Header: Kursname + "Woche X – Lernplan" + exam countdown pill
Day tabs: Tag 1 … Tag N (clickable, active state, done state in success color)
Per-day panel (shown on tab click):
  ├── Panel header: day badge + topic name + subtitle (what this day covers)
  ├── Theorie-Prompt button(s): sendPrompt() calls for explanations
  ├── Übungs-Prompt button(s): sendPrompt() calls for interactive exercises
  ├── Checklist: 3–5 learning goals the user can tick off
  └── Footer: "Tag als erledigt markieren" button + goal progress label
Week footer: progress bar (done days / total) + label
```

#### sendPrompt() button rules

Every prompt button must:

- Have a **title** (what the prompt does, ≤8 words)
- Have a **subtitle** (one-liner describing the interaction style, e.g. "interaktiv – du löst, ich korrigiere")
- Display a `↗` arrow on the right (via CSS `::after`)
- Call `sendPrompt('...')` with a self-contained, specific prompt — not vague ("erkläre Relationen") but precise ("Erkläre mir die Relationsmatrix aus dem Skript von Schwenker. Ich brauche: ...")

Prompt types to include per day:

- **Theorie:** Ask Claude to explain the topic with examples and exam traps
- **Interaktiv:** Ask Claude to give exercises one at a time, wait for user answer, then correct
- **Klausurnah:** Ask Claude to pose an exam-style task from the actual Altklausur content
- **Fehleranalyse** (day 7 / review days only): Ask Claude to analyze gaps after a practice exam

#### Checklist behavior

Use JS `onclick` to toggle a `.checked` class on `<li>` elements. Checked items show a ✓ in a small box, the text gets `text-decoration: line-through`, and the goal counter updates (e.g. "2/3 Ziele"). No storage needed — state is session-only.

#### Day completion

"Tag als erledigt markieren" button: adds the day index to a `doneDays[]` array, switches the tab to `.done` style (success color border + background), advances to the next tab automatically, updates the week progress bar.

#### Exam-day (last day of each week)

Structure differently from regular days:

- No Theorie-Prompt
- "Vor dem Start" info card: remind user to work on paper, no peeking, time limit
- 3 sequential exam prompts (Aufgabe 1, 2, 3…) — one per major topic
- A "Fehleranalyse & Prioritäten" prompt at the end
- More checklist items (5) reflecting the full exam scope

#### Content rules

- Base the daily topics on the actual course curriculum and Altklausur frequency analysis if available in project context.
- Week 1 = foundations + highest-frequency exam topics. Later weeks = harder topics + full practice exams.
- Each day should be completable in ~60–90 minutes.
- Day 7 of each week = mini-practice exam covering that week's content.
- Prompts must reference actual content: real relation sets, real Altklausur question formats, real formulas — not generic placeholders.

#### JS requirements

```javascript
var doneDays = [];
function showDay(idx) {
  /* toggle .active on panels and tabs */
}
function toggleCheck(li) {
  /* toggle .checked, update counter */
}
function markDone(idx) {
  /* add to doneDays, update tab style, advance, update progress bar */
}
function updateWeekProgress() {
  /* update width of .progress-fill and label text */
}
```

**Do not use `localStorage`** — state is session-only.
