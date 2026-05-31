## Visual Design Rules (Workflow 1)

Before rendering a slide summary widget, call `read_me` with `["mockup"]` to load the design system. Then build the HTML widget following these rules:

### Required sections (in order)

1. **Header** — module name + subtitle (e.g. "C# · DHBW Heidenheim")
2. **Topic blocks** — one card per conceptual group, numbered with slide references
3. **Übungsaufgaben** — inline in the widget, amber-styled, covering exam exercises from the slides
4. **Lückencheck** — red-styled warning block at the bottom flagging missing topics

### Card anatomy

Each topic block card must contain:

- A labeled badge (e.g. `Grundlage`, `Konzept`, `Reihenfolge`) with semantic color
- The concept explanation in `card-body` (13px, secondary color)
- An `Eigene Worte` block: italic prompt in a secondary-background box
- ⚠️ warnings for memorization-critical content (formulas, definitions, legal paragraphs)

### Layout patterns

- Use `grid2` (2-column CSS grid) for side-by-side comparisons (e.g. statisch vs. dynamisch, abstract vs. sealed)
- Use `compare-table` for structured comparison tables (e.g. Override/Overwrite/Overload)
- Use `order-list` (counter-based list) for sequential steps (e.g. constructor execution order)
- Use `methods-grid` (2-column grid) for method/property inventories

### Color semantics

Use badge colors consistently to encode meaning — not decoration:

- `badge-purple` — fundamental concepts, base-level definitions
- `badge-teal` — OOP design concepts, architectural patterns
- `badge-blue` — sequences, ordering, procedural steps
- `badge-red` — errors, exceptions, things that throw/fail, sealed
- `badge-amber` — exam exercises, warnings, edge cases
- `badge-purple` — abstract, interfaces

### Styling rules

- All text via CSS variables (`--color-text-primary`, `--color-text-secondary`)
- No hardcoded colors except within the defined badge/warn patterns
- `font-family: var(--font-mono)` for all inline code
- Cards: `border: 0.5px solid var(--color-border-tertiary)`, `border-radius: var(--border-radius-lg)`
- Lückencheck block: red border + red background tint, bottom of widget
- Übungsaufgaben blocks: amber border + amber background tint

### What NOT to do

- Do not put explanatory prose inside the widget — that goes in the response text outside the tool call
- Do not use emoji inside the widget
- Do not use bold mid-sentence; bold is for card titles and section labels only
- Do not use dark or colored outer backgrounds
