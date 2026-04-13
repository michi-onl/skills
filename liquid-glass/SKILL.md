---
name: liquid-glass
description: Create or migrate websites and personal pages to Apple's Liquid Glass design language — translucent blurred panels, pill-shaped grouped controls, concentric rounded corners, and responsive navigation that reflows between mobile and desktop. Use this skill whenever the user asks to build a website, landing page, portfolio, personal site, or homepage with a glassy, translucent, frosted, or "Apple-style" look. Also trigger when the user mentions "Liquid Glass", "glassmorphism", "frosted glass UI", "blur effect website", "glass navbar", or wants to modernize/refresh a site's visual style to feel premium or Apple-like. Supports plain HTML/CSS/JS, Next.js (React), Zola (Rust SSG), and design systems like shadcn/ui and Bootstrap. Even if the user doesn't name a framework, use this skill when the visual intent is glassy/translucent.
---

# Liquid Glass Web Design

Build websites using Apple's Liquid Glass design principles adapted for the web. This is NOT about replicating native iOS/macOS controls. It's about translating the *design philosophy* — translucent layered surfaces, grouped pill-shaped controls, concentric corner radii, scroll-aware blurring, and content-first hierarchy — into responsive web interfaces.

## Before you start

1. Read `references/design-system.md` for the CSS variables, blur values, corner radii, spacing, and color tokens.
2. Identify the target framework from the user's request. Then read the relevant framework reference:
   - Plain HTML/CSS/JS → `references/html.md`
   - Next.js / React → `references/nextjs.md`
   - Zola (Rust SSG) → `references/zola.md`
   - shadcn/ui → `references/shadcn.md`
   - Bootstrap → `references/bootstrap.md`
3. If migrating an existing site, audit its current navigation structure and controls before applying the glass layer.

## Core design principles

### 1. Two-layer architecture
Liquid Glass creates exactly two visual layers:
- **Content layer**: The page body, images, text, cards. This is what matters. It sits behind everything.
- **Glass layer**: Navigation bars, toolbars, floating action groups, sidebars. These float above content using `backdrop-filter: blur()` and semi-transparent backgrounds. They exist to *serve* the content layer, not compete with it.

Never put glass on content cards, article bodies, or hero sections. Glass is for functional chrome only — navigation, controls, toolbars.

### 2. Grouped controls in pills
Controls that perform related actions share a single pill-shaped glass container. Unrelated actions get their own pill. This is the most distinctive Liquid Glass pattern.

**Grouping rules for common website elements:**

Homepage / personal site navbar:
- **Left pill**: Site logo/name + home link (they're the same action conceptually)
- **Center or right pill**: Primary nav links grouped together (About, Projects, Blog)
- **Separate pill**: Search icon or CTA button (different intent)

Blog/article toolbar:
- **One pill**: Share + bookmark (content actions)
- **Separate pill**: Table of contents toggle or settings

Portfolio toolbar:
- **One pill**: Filter/sort controls
- **Separate pill**: Grid/list view toggle

Footer actions:
- **One pill**: Social links grouped (GitHub, Twitter, email)
- **Separate pill**: RSS or theme toggle

The test: "Would a user reach for these in the same mental moment?" If yes, group them.

### 3. Concentric corner radii
Nested elements use progressively smaller radii. If a container has `border-radius: 24px`, its children use `border-radius: 16px`, and their children use `border-radius: 12px`. This creates visual harmony. The outer radius minus the padding between elements should roughly equal the inner radius.

### 4. Responsive reflow
On desktop (>768px), the glass navbar sits at the top as a floating bar with generous margin from screen edges. On mobile (<768px), the primary nav becomes a bottom-anchored glass bar (like a tab bar), and secondary actions move behind a menu or to the top. The glass bar should never span the full viewport width on desktop — it floats with rounded ends.

**Desktop layout:**
```
┌──────────────────────────────────────────────────┐
│                                                  │
│   ╭─Logo─Home─╮  ╭─About─Projects─Blog─╮  ╭─🔍─╮│
│   ╰───────────╯  ╰─────────────────────╯  ╰───╯ │
│                                                  │
│              [ page content ]                    │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Mobile layout:**
```
┌──────────────────┐
│  ╭─Logo─╮  ╭─☰─╮│  ← top bar, minimal
│  ╰──────╯  ╰───╯│
│                  │
│ [ page content ] │
│                  │
│╭─🏠──📁──📝──🔍─╮│  ← bottom glass tab bar
│╰─────────────────╯│
└──────────────────┘
```

### 5. Scroll-edge effect
When content scrolls beneath a glass bar, increase the blur intensity and add a subtle gradient fade at the scroll edge. This maintains legibility. On scroll, the glass bar can optionally become slightly more opaque.

### 6. Color discipline
Glass elements inherit their tint from the content beneath them. Don't apply heavy brand colors to glass surfaces. Use:
- Near-transparent white (`rgba(255,255,255,0.15)`) in light mode
- Near-transparent dark (`rgba(0,0,0,0.2)`) in dark mode
- One accent color max for the currently active nav item
- Text on glass: use high-contrast colors, not mid-grays

### 7. Avoid over-glassing
Apply glass to at most 2-3 elements on any given page. Navbar + one floating toolbar is fine. Navbar + sidebar + toolbar + footer all in glass is too much. When in doubt, leave it solid.

## Common page patterns

### Personal site / portfolio homepage
- Floating glass navbar (top, desktop) / bottom tab bar (mobile)
- Hero section: full-bleed image or gradient, NO glass overlay
- Content cards: solid background with concentric radii, not glass
- One floating action: theme toggle or contact CTA in a small glass pill, fixed position

### Blog / article page
- Glass navbar persists from homepage
- Reading progress bar (thin, at top of viewport, no glass needed)
- Optional: floating glass pill with share/bookmark at bottom-right
- Article body: clean, no glass anywhere near the text

### Project showcase / gallery
- Glass navbar
- Optional glass filter bar (sticky, below navbar)
- Grid items: solid cards, not glass
- Lightbox overlay: subtle glass background blur on the backdrop

## Implementation checklist
- [ ] `backdrop-filter: blur()` with `-webkit-backdrop-filter` fallback
- [ ] `@supports (backdrop-filter: blur())` progressive enhancement
- [ ] Reduced-motion media query: disable blur animations, use solid fallback backgrounds
- [ ] Reduced-transparency preference: swap glass for solid backgrounds with matching colors
- [ ] Touch targets ≥ 44px on mobile
- [ ] Glass elements have `will-change: backdrop-filter` only when animating
- [ ] Test with vibrant/busy background images — if text is unreadable, increase opacity or blur
- [ ] Concentric radii verified on all nested elements
- [ ] Mobile bottom bar clears safe area (`env(safe-area-inset-bottom)`)
