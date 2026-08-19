# The WidgetStar Embed Contract

Everything here is derived from the two shipped loaders, `https://u.widget.st/ar.js`
(host page) and `https://widget.st/js/iframe.js` (your page). When behaviour is unclear,
re-download and read them — they are small and unminified enough to follow.

## Two halves

```
Installer's site                          Your host
─────────────────────────────────────     ────────────────────────────
<script src="…/ar.js">                    widget.html
  defines <ws-widget>                       <script src="…/js/iframe.js">
  creates <iframe src=                        parses ?settings → window.WS.settings
    "https://widget.st/embed/<iid>">          forces html/body reset + max-content
       │                                      ResizeObserver(body) ──┐
       │  ◄── postMessage ws:resize {w,h} ────────────────────────────┘
       └──── postMessage ws:resize {width,height} ──►  (only if host set width/height)
```

## Host side: `ar.js` and `<ws-widget>`

Loaded once per page: `<script src="https://u.widget.st/ar.js"></script>`.
It defines the `ws-widget` custom element.

### Attributes

| Attribute | Meaning |
| --- | --- |
| `type` | Widget slug. Matches against the built-in table first. |
| `iid` | Instance id. This is what identifies the configured instance. |
| `embed` | `iframe` or `script`. Only consulted when `type` is not a built-in. |
| `name` | Instance name, forwarded as `?name=` and used as the iframe `title`. |
| `settings` | URL-encoded JSON, per-element settings override. |
| `width` / `height` | CSS size. Overrides autosizing and switches your page to fill mode. |
| `preview` | Boolean. Dashboard preview only — fails everywhere except widget.st. |
| `auto` / `wid` / `predefine` | Auto-provisioning path: creates an instance from the page URL instead of using a fixed `iid`. |

All of these are observed attributes — changing one re-renders. The element also exposes a
`.reload()` method, useful when telling an installer how to refresh a widget after a
settings change.

### Embed-mode resolution (in order)

1. `type` matches the built-in table → that mode wins, **your `embed` attribute is ignored**.
   Built-ins: `chat` = iframe; `atabook`, `calendar`, `comments`, `contact`, `hc`, `lastfm`,
   `like`, `polls`, `rating`, `reactions`, `status`, `weather`, `webring` = script.
2. `embed="script"` or `embed="iframe"` → that mode.
3. Otherwise → `iframe`.

This is why slug collisions are silently destructive: a widget slugged `weather` is forced
into script mode and your iframe page is never loaded.

### The visibility rule (cause of most "nothing renders" reports)

`ar.js` injects:

```css
ws-widget[data-embed="iframe"] { display: inline-block; width: 0; height: 0; }
ws-widget[data-embed="iframe"] iframe { border: none; width: 100%; height: 100%; overflow: hidden; visibility: hidden; }
ws-widget[data-sized] iframe { visibility: visible; }
```

The host element starts at **0×0 with a hidden iframe**. `data-sized` is set only when:

- a `ws:resize` message arrives from your page (→ requires `iframe.js`), **or**
- the installer set *both* `width` and `height` on the element.

No `iframe.js` and no explicit size means the widget is permanently invisible, with no error
in the console. This is the single most common failure.

### Resize protocol

- **Child → parent**: `{ type: "ws:resize", w: <px>, h: <px> }`, posted on every
  `ResizeObserver` tick of `document.body` plus once on init. The parent writes those as
  pixel `style.width`/`style.height` on the `ws-widget` element (skipping either axis the
  installer pinned via attribute) and sets `data-sized`.
- **Parent → child**: `{ type: "ws:resize", width, height }`, sent only when the installer
  pinned a size. `iframe.js` responds by setting `html`/`body` to `100%` — **fill mode**.

Because the iframe's height follows your content, anything in your CSS that derives size from
the viewport (`vh`, `vw`, `100%` height chains rooted at `html`) creates a measure → resize →
measure loop. The starter template avoids this by design.

## Your side: `iframe.js`

```html
<script src="https://widget.st/js/iframe.js"></script>
```

Put it first in `<head>`. It is synchronous and does three things:

**1. Settings.** Reads the `settings` query parameter, `JSON.parse`s it, and assigns
`window.WS.settings`. Any failure yields `{}` — never `null`, never `undefined`, so
`WS.settings.foo` is always safe to read but is very often absent. The raw query parameter is
also readable directly if you need it before the script runs.

**2. A forced reset.** It appends this stylesheet, so it wins over anything with equal
specificity that you declared *earlier*:

```css
html, body { margin: 0; padding: 0; overflow: hidden; background: transparent; }
body       { width: max-content; height: max-content; }
```

Consequences you must design around:

| Injected rule | What breaks | Do this instead |
| --- | --- | --- |
| `body { width: max-content }` | `width: 100%` / percentage widths collapse or resolve circularly | Size your root with `max-content` + `min-width`/`max-width` in px |
| `overflow: hidden` on html+body | Dropdowns, tooltips, focus rings, drop shadows are clipped | Keep overlays inside the root's padding, or expand the root when open |
| `background: transparent` | The host page shows through — often desirable, sometimes not | Paint the background on your root element, not on `body` |
| `margin: 0` on body only | Margins on your *first/last child* still escape the measured box | Use padding on the root wrapper, not margins on children |
| body measured by `getBoundingClientRect()` | `position: fixed` children contribute nothing → height measures 0 | Use `position: relative/absolute` inside an in-flow root |

**3. Autosizing.** A `ResizeObserver` on `body` posts `ws:resize` upward. Late-loading fonts
and images therefore resize the widget correctly on their own — but they also cause a visible
jump, so set explicit `width`/`height` on images and prefer system fonts.

### Supporting both sizing modes

Detect fill mode by listening for the parent's message, then switch your root's sizing:

```js
addEventListener("message", (e) => {
  if (e.data?.type === "ws:resize" && (e.data.width || e.data.height)) {
    document.documentElement.classList.add("ws-fill");
  }
});
```

```css
#ws-root            { width: max-content; min-width: 220px; max-width: 420px; }
.ws-fill #ws-root   { width: 100%; max-width: none; height: 100%; }
```

This is already wired up in `assets/starter-widget.html`.

### Security

`WS.settings` comes from a URL parameter that the installing site controls per element
(`settings="%7B%22coloring%22%3A%22system%22%7D"`). Treat every value as hostile input:
`textContent` not `innerHTML`, validate enums against an allow-list, clamp numbers, and
reject non-`https:` URLs before putting them in `src`/`href`.

## Origin binding

`https://widget.st/embed/<iid>` is served with a per-instance CSP, e.g.

```
content-security-policy: frame-ancestors widget.st *.widget.st example.org *.example.org http://localhost:* http://*.localhost:* http://127.0.0.1:*;
```

An instance created for one site cannot be framed on another — the browser blocks it and the
host sees an empty box. Every site needs its own instance and `iid`. `http://localhost:*` and
`127.0.0.1` are allowed, so an installer can develop locally with a production instance.

## Script mode

Only relevant if the widget is `embed="script"`. `ar.js` appends
`<script src="https://widget.st/embed/<iid>?name=…&settings=…&href=…">`, waits for `onload`,
then calls a global the script must have defined:

```js
window._ws_embed_<iid> = function (element, getCaptchaToken, resilientFetch, createOwnerAuth, resilientSubmit) { … }
```

The global is deleted immediately after the call. Arguments:

| Argument | Purpose |
| --- | --- |
| `element` | The `<ws-widget>` element itself. Append your DOM to it. |
| `getCaptchaToken(force?)` | Resolves a Turnstile token. Check `GET /embed/<iid>/needs_captcha` first — `ar.js` does this for you before calling. |
| `resilientFetch(url, init)` | `fetch` that transparently retries through a hidden bridge iframe when the host's CSP blocks `connect-src`. **Use this instead of `fetch` for anything hitting widget.st.** |
| `createOwnerAuth({origin, instanceId})` | Owner-token flow (`ensure()`, `getToken()`, `clearToken()`) for owner-only controls, via popup or parent bridge. |
| `resilientSubmit(form)` | Form submission that survives a blocking `form-action` CSP. |

You run inside the installer's page: their CSS cascades into your markup, their CSP governs
your requests, and a thrown error is visible in their console. Namespace class names, scope
styles tightly, and never assume `fetch`, cookies or `localStorage` are available.

The dashboard's script-mode fields differ from the iframe fields shown in the create form —
switch **Embed type** to `script` on the General tab and read the fields presented there
rather than assuming a Page URL.
