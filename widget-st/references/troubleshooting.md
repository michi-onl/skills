# Troubleshooting

Symptoms are mechanical here. Match the symptom, apply the fix, don't start rewriting CSS.

## Nothing appears at all; DevTools shows `<ws-widget>` at 0×0

The element only becomes visible when `data-sized` is set, which needs a `ws:resize` message
from your page. In order of likelihood:

1. **`iframe.js` is missing** from the widget page. Add
   `<script src="https://widget.st/js/iframe.js"></script>` as the first thing in `<head>`.
2. **A JS error killed the page before layout.** Open the iframe URL directly and check the
   console.
3. **`<body>` is genuinely empty** at load and stays empty — e.g. the render is awaiting a
   fetch that fails. Render a placeholder synchronously, then swap in the data.
4. **Everything in the body is `position: fixed`.** The measured box is
   `document.body.getBoundingClientRect()`; fixed elements are out of flow and contribute
   nothing, so `h` is 0. Wrap content in an in-flow root.

Quick check: in the iframe's console, `document.body.getBoundingClientRect()`. If width or
height is 0, the parent is behaving correctly and your layout is the problem.

## The iframe is there but shows a blank white box

Framing is blocked, so nothing loads inside it. The console shows a "Refused to display … in
a frame" error.

- Your host sends `X-Frame-Options: DENY` or `SAMEORIGIN`, or a CSP with
  `frame-ancestors 'self'` / `'none'`. Run `python3 scripts/check_widget.py <url>` to confirm,
  then loosen it on the host.
- The Page URL is `http://` on an `https://` site → mixed content, blocked silently in some
  browsers. Always use HTTPS.
- The installer's own CSP restricts `frame-src`/`child-src` and doesn't allow `widget.st`.
  That is on their side; they need `frame-src https://widget.st`.

## "Preview embeds can only be loaded from WidgetStar"

The snippet contains `preview` / `preview=true`. Preview embeds are refused off-site by
design. Remove the attribute — the install snippet is:

```html
<ws-widget type="<slug>" iid="<instanceId>" embed="iframe"></ws-widget>
```

The snippet shown on widget.st's own landing page and dashboard previews is not install code.

## Works on my site, not on someone else's

Instances are origin-bound. `https://widget.st/embed/<iid>` is served with
`frame-ancestors` listing only the site that instance belongs to (plus widget.st and
localhost). The second site needs its own instance and its own `iid` — the same `iid` cannot
be shared across domains.

## Content is clipped — dropdown, tooltip, shadow cut off

`iframe.js` sets `overflow: hidden` on both `html` and `body`, and the iframe is exactly as
tall as the content. Anything drawn outside the root's box is cut.

- Keep overlays inside the root and let the widget grow when they open — the
  `ResizeObserver` will resize the iframe automatically.
- Add padding on the root to make room for shadows and focus rings.
- Nothing can escape the iframe. A menu that must overlay the host page is not possible in
  iframe mode; that needs script mode.

## Width collapses / everything is squished into one column

`body` is `width: max-content`, so percentage widths have no definite containing block.

```css
/* wrong */  #ws-root { width: 100%; }
/* right */  #ws-root { width: max-content; min-width: 220px; max-width: 420px; }
```

Percentages only work in fill mode (installer set `width`/`height` on the element, which makes
`iframe.js` set `html`/`body` to `100%`). Support both via the `.ws-fill` class pattern in
`assets/starter-widget.html`.

## The widget grows, shrinks, grows — flickering forever

A `ResizeObserver` feedback loop: the iframe's size follows your content, and your content
follows the iframe's size.

Remove every viewport-derived size: `vh`, `vw`, `vmin`, `vmax`, `height: 100%` chains rooted
at `html`, and JS that reads `window.innerWidth`/`innerHeight` to lay out. Use px, `ch`, `em`,
`min-width`/`max-width`. If you need a scroll region, give a wrapper a fixed px height and
`overflow: auto` — never `body`.

## Settings are ignored

1. **Key mismatch.** The dashboard key (hover the label to see it) must equal the string you
   read from `WS.settings`. Case-sensitive.
2. **Read too early.** `WS.settings` exists as soon as `iframe.js` has run; if your script is
   `async`/`defer`-ordered before it, you get `undefined`. Load `iframe.js` first in `<head>`.
3. **Empty is normal.** In the store preview and before configuration, `WS.settings` is `{}`.
   If it renders nothing then, it looks broken to every prospective installer.
4. **Malformed override.** A per-element `settings="…"` attribute must be *URL-encoded JSON*.
   Invalid JSON silently yields `{}` — it does not throw and does not warn.
5. **Cached iframe.** Settings are in the iframe URL; after changing them the installer may
   need a hard reload, or `document.querySelector("ws-widget").reload()`.

## Layout jumps on load

Late-arriving fonts and images change the measured size, which correctly triggers a resize —
but visibly. Set explicit `width`/`height` on `<img>`, prefer system font stacks, and avoid
web fonts that shift metrics.

## Script-mode widget throws inside the host page

Your code runs on their origin under their CSP.

- `fetch` blocked by `connect-src` → use the injected `resilientFetch`, which falls back to the
  widget.st bridge iframe automatically.
- Form posts blocked by `form-action` → use `resilientSubmit`.
- Their CSS is bleeding into your markup → namespace class names and scope every selector.
- `window._ws_embed_<iid>` must be defined by the served script before `onload` fires, and it
  is deleted right after being called — don't rely on it existing later.
