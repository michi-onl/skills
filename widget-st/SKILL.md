---
name: widget-st
description: "Build widget.st (WidgetStar) widgets: iframe/script embeds, WS.settings schema, autosizing, dashboard fields. Trigger: \"widget.st\", \"WidgetStar\", \"ws-widget\"."
---

# WidgetStar Widget Builder

Build a widget for [widget.st](https://widget.st) end to end: the embeddable page, the
settings schema, the dashboard entry, and the install snippet handed to site owners.

The hard part is not the widget's own logic — it is the embed contract. A widget that looks
perfect standalone renders as a **0×0 invisible element** on a real site if it misses one
script tag. Everything in this skill exists to prevent that.

## Scope

**Target**: a working widget listed on widget.st, installable via `<ws-widget>` on third-party sites
**Acceptance criteria**: renders at the right size on a real installer's site, respects every declared setting, degrades to sane defaults when settings are empty
**Off-limits**: the dashboard is login-gated — never guess at values on the user's behalf; produce a fill-in sheet and let them paste. Never publish or change widget Status without asking.

## Division of labour

| Claude does | The user does |
| --- | --- |
| Writes and verifies the widget page | Logs in at widget.st/auth/login |
| Runs the local harness + validator | Creates the widget on the Dashboard → General tab |
| Produces exact dashboard field values | Pastes them, saves, opens Settings/Appearance tabs |
| Produces the installer snippet | Installs on the target site and confirms |

## Workflow

### 1. Pick the embed type

**iframe** — you host an HTML page, widget.st loads it in an iframe. You control the whole
stack, no review of your JS, works with any framework. **Default choice; the rest of this
skill assumes it.**

**script** — widget.st serves JS from `/embed/<iid>` that runs directly in the host page's
DOM. Faster and stylable by the host, but the code runs on the host's origin and inherits
their CSP. Only pick this if the user specifically needs in-page DOM access. See
`references/embed-contract.md` § Script mode for the `window._ws_embed_<iid>` contract
before promising anything here.

### 2. Build the page

Start from `assets/starter-widget.html` — it is a complete, working widget with the
contract already satisfied. Read `references/embed-contract.md` before deviating from it.

Five rules that cause almost every broken widget:

1. **`<script src="https://widget.st/js/iframe.js"></script>` first in `<head>`.** Without it
   the widget never reports its size, and `ws-widget` keeps it at `width:0;height:0;visibility:hidden`.
   Not "badly sized" — completely invisible.
2. **Never use `vw`/`vh` units, and never size anything from the viewport.** The iframe is
   sized *from* your content; sizing content *from* the iframe is a feedback loop that
   oscillates forever.
3. **Size the outermost element intrinsically** (`width: max-content` + `min-width`/`max-width`
   in px). `body` is set to `width: max-content`, so percentage widths have nothing to resolve
   against and collapse.
4. **No `position: fixed`, and keep overlays inside the measured box.** `html`/`body` get
   `overflow: hidden`, and fixed elements contribute nothing to the measured height — dropdowns
   and tooltips get clipped or measure as zero.
5. **`textContent`, never `innerHTML`, for anything from `WS.settings`.** Settings arrive as a
   URL query parameter and installers can override them per element, so they are untrusted input.

### 3. Read settings defensively

`window.WS.settings` is an object parsed from the `settings` query param. It is `{}` in the
dashboard preview, `{}` before the installer configures anything, and `{}` if the JSON fails
to parse. Every key needs a fallback:

```js
const S = (window.WS && window.WS.settings) || {};
const title = typeof S.title === "string" && S.title.trim() ? S.title.trim() : "Untitled";
```

A widget that renders nothing on empty settings looks broken in the store preview, which is
the first thing anyone sees.

### 4. Verify locally — before anything is published

```bash
cd <folder containing the widget page>
cp ~/.claude/skills/widget-st/scripts/harness.html .
python3 -m http.server 8000
# open http://localhost:8000/harness.html
```

`harness.html` reproduces what `ar.js` does on a real site: it frames the page, applies the
same zero-size/hidden CSS, listens for `ws:resize`, and logs every message. If the widget
stays hidden there, it will stay hidden in production. Test with settings empty, with all
settings filled, and with the host width/height override.

Then run the static checks:

```bash
python3 ~/.claude/skills/widget-st/scripts/check_widget.py --file widget.html
python3 ~/.claude/skills/widget-st/scripts/check_widget.py https://example.com/widget/   # after publishing
```

The URL mode is the only way to catch framing headers, which are the second most common
cause of a blank widget.

### 5. Publish the page

Requirements: **HTTPS**, absolute URL, stable path, and the host must permit framing —
no `X-Frame-Options: DENY|SAMEORIGIN`, no `Content-Security-Policy: frame-ancestors 'self'`.
Netlify, Cloudflare Pages, GitHub Pages and Nekoweb are fine by default; many PaaS defaults
and most WordPress security plugins are not. Re-run `check_widget.py` against the live URL.

### 6. Fill in the dashboard

Log in → Dashboard → create widget. Only the **General** tab exists until the first save;
Settings, Appearance and Status unlock afterwards.

Read `references/dashboard.md` and produce a fill-in sheet with every field's exact value,
including the slug rules and the installer-facing Notes/Extra steps. Two things to get right
the first time:

- **The slug must not collide with a built-in** (`atabook`, `calendar`, `chat`, `comments`,
  `contact`, `hc`, `lastfm`, `like`, `polls`, `rating`, `reactions`, `status`, `weather`,
  `webring`). A colliding slug forces the built-in's embed mode and silently ignores yours.
- **Settings keys must match the code exactly.** Hovering a settings label in the dashboard
  reveals its key; that key is `WS.settings.<key>`. Write the schema and the code from one
  shared list.

### 7. Install and verify on the real site

Hand over exactly this — nothing else:

```html
<!-- once, in <head> -->
<script src="https://u.widget.st/ar.js"></script>

<!-- where the widget should appear -->
<ws-widget type="<slug>" iid="<instanceId>" embed="iframe"></ws-widget>
```

Never hand over a snippet containing `preview` or `preview=true`. Those only render on
widget.st itself; anywhere else they produce *"Preview embeds can only be loaded from
WidgetStar"*. The dashboard's preview snippet is not install code.

**Each instance is bound to the site it was created for.** widget.st serves
`frame-ancestors <that site> ... http://localhost:*` per instance, so a second site needs
its own instance and its own `iid`. Expect this question and answer it before it is asked.

## When it doesn't work

Go to `references/troubleshooting.md`. It maps every symptom (invisible, clipped, blank box,
infinite resize, settings ignored, works-here-not-there) to its cause. Do not start guessing
at CSS before checking it — the symptoms are distinctive and the causes are mechanical.

## References

| File | Read it when |
| --- | --- |
| `references/embed-contract.md` | Building the page; anything about sizing, settings, messaging, or script mode |
| `references/dashboard.md` | Filling in the dashboard, writing the settings schema, publishing or deprecating |
| `references/troubleshooting.md` | Any symptom at all |
| `assets/starter-widget.html` | Starting a new widget — copy this, don't write from scratch |
| `scripts/harness.html` | Local visual verification |
| `scripts/check_widget.py` | Static + header validation |
