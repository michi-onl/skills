# The widget.st Dashboard

The dashboard is behind a login, so Claude cannot fill it in. Produce a **fill-in sheet** —
every field with its exact final value — and let the user paste. Ask before anything that is
publicly visible or destructive (Status changes, Delete).

## Order of operations

1. User logs in at `https://widget.st/auth/login`.
2. Dashboard → create widget. **Only the General tab exists.**
3. Save. The Settings, Appearance and Status tabs unlock.
4. Fill the schema tabs, save again.
5. Install an instance on the target site to get an `iid`.

Consequence: the widget page must already be live at its final URL before step 2, or the
General tab gets a placeholder that someone has to remember to fix.

## General tab

| Field | Rules and guidance |
| --- | --- |
| **Slug** | Lowercase letters, numbers, hyphens; must start with a letter. Permanent-feeling identifier — used as `type="<slug>"` in every install snippet. **Must not collide with a built-in** (`atabook`, `calendar`, `chat`, `comments`, `contact`, `hc`, `lastfm`, `like`, `polls`, `rating`, `reactions`, `status`, `weather`, `webring`); a collision silently forces that built-in's embed mode. Check `https://widget.st/widget/<slug>` for a 200 before committing to one. |
| **Name** | Display name in the store and dashboard. Title case, no "Widget" suffix unless the name needs it. |
| **Icon** | Optional. Small square image; it sits next to the name in the store listing. |
| **Summary** | One line, shown in listings. Say what it does, not that it is a widget. |
| **Description** | Longer store copy. Markdown support is limited to **bold**, *italic*, links, `code`, and `-` bullet lists — no headings, tables, or images. |
| **Embed type** | `iframe` or `script`. See `embed-contract.md`; the remaining fields change with this choice. |
| **Page URL** (iframe) | Absolute `https://` URL of your page. Must allow framing and must load `https://widget.st/js/iframe.js`. |
| **Instructions** | Pre-filled reminder about `iframe.js` and `WS.settings`. Nothing to do unless you want to extend it. |
| **Disable dashboard preview** | Leave off. The preview is what people judge the widget by. Only enable it if the widget genuinely cannot render without live user data. |
| **Preview width / height** | Optional CSS sizes (`100%`, `300px`) for the dashboard preview box. Set these when the widget is much wider or taller than the default box, otherwise leave blank and let autosizing work. |
| **Notes** | Installer-facing text shown with the install snippet. Simple markdown. Placeholders `{{instanceId}}`, `{{slug}}`, `{{embedMode}}` are substituted per instance. |
| **Extra steps** | Additional install steps beyond pasting the snippet — API keys, a required container element, DNS, whatever. Keep to numbered, verifiable actions. |
| **Installer preview** | Read-only rendering of what the installer will see. Check it after every edit to Notes/Extra steps. |

The install snippet installers receive is:

```html
<script src="https://u.widget.st/ar.js"></script>

<ws-widget type="{{slug}}" iid="{{instanceId}}" embed="{{embedMode}}"></ws-widget>
```

Optional attributes worth documenting in **Notes** when they apply: `width`/`height` (CSS
values that override autosizing — mention it only if your widget handles fill mode), and
`settings` (URL-encoded JSON overriding settings for that one element).

## Settings and Appearance tabs

Two schemas with the same shape — `key`, `label`, `type`. The split is conventional, not
technical: both land in the same `WS.settings` object.

- **Settings** — behaviour and data: source URLs, usernames, item counts, refresh interval, text.
- **Appearance** — visuals: colors, font, corner radius, layout variant, light/dark mode.

Rules that matter:

1. **`key` is the contract.** `WS.settings.<key>`, verbatim. Hovering a label in the dashboard
   shows the key — that is how installers find them for per-element `settings=` overrides.
   Use lowercase, no hyphens (so `WS.settings.showAvatar` or `WS.settings.show_avatar`, picked
   once and applied consistently).
2. **Write the schema and the code from one list.** Draft the key list first, put it in a
   comment at the top of the widget page, then enter it in the dashboard. Silent typos here
   are the most common "my setting does nothing" cause.
3. **Every key needs a code-side default.** Fields are empty until an installer fills them, and
   the store preview always runs with `{}`.
4. **The available field types are whatever the tab's type dropdown offers.** Read the actual
   options in the UI rather than assuming; pick the most constrained type that fits (a select
   over a free-text field, a color picker over a hex string) so you validate less.
5. **Validate anyway.** Even a constrained field arrives as a string in a URL parameter that the
   host page can rewrite. Allow-list enums, clamp numbers, reject non-`https:` URLs.
6. **Renaming a key breaks every existing install.** Instances keep their stored values against
   the old key. Add a new key and read both for a while instead.

## Status tab

| Status | Effect | Use when |
| --- | --- | --- |
| **Active** | Visible in the store, new instances allowed | Normal |
| **Deprecated** | Visible only to existing installers, no new instances | Superseded by a replacement widget |
| **Archived** | Invisible everywhere, existing embeds keep working, no new instances | Retiring quietly |

**Delete** permanently removes the widget and all instances and breaks it on every site that
has it installed. It is irreversible. Never trigger it on the user's behalf; if they ask,
confirm the install count shown in the delete box first and prefer Archived unless they
explicitly want it gone.

## Publishing checklist

- [ ] Page live at the exact Page URL over HTTPS, framing allowed (`check_widget.py <url>` clean)
- [ ] Renders correctly in `harness.html` with `{}` settings and with every setting filled
- [ ] Every schema key read in the code, every code key present in the schema
- [ ] Slug free and non-colliding
- [ ] Summary, Description, Icon filled — this is the store listing
- [ ] Dashboard preview shows something meaningful with no configuration
- [ ] Notes/Extra steps reviewed in Installer preview
- [ ] Installed on one real site and verified there before Status → Active
