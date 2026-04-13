# Liquid Glass Design System Tokens

## CSS Custom Properties

Paste these into your root stylesheet or Tailwind config. Every glass component references these variables.

```css
:root {
  /* --- Glass surface --- */
  --glass-bg-light: rgba(255, 255, 255, 0.18);
  --glass-bg-dark: rgba(0, 0, 0, 0.22);
  --glass-bg: var(--glass-bg-light);
  --glass-border: rgba(255, 255, 255, 0.3);
  --glass-border-dark: rgba(255, 255, 255, 0.08);
  --glass-shadow: 0 2px 16px rgba(0, 0, 0, 0.08);
  --glass-shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.12);

  /* --- Blur --- */
  --blur-standard: 20px;       /* navbar, toolbar */
  --blur-heavy: 40px;          /* modal backdrop, overlays */
  --blur-subtle: 12px;         /* secondary glass, less prominent */
  --blur-scroll-boost: 28px;   /* when content scrolls beneath */

  /* --- Corner radii (concentric system) --- */
  --radius-outer: 24px;        /* outermost glass container */
  --radius-inner: 16px;        /* items inside glass container */
  --radius-control: 12px;      /* buttons, inputs inside pills */
  --radius-badge: 8px;         /* tags, small chips */
  --radius-full: 9999px;       /* fully round pills */

  /* --- Spacing --- */
  --glass-padding: 8px;        /* padding inside glass pill */
  --glass-gap: 6px;            /* gap between items in a pill */
  --glass-item-padding: 8px 14px; /* padding inside each nav item */
  --glass-float-margin: 16px;  /* margin between glass bar and viewport edge */

  /* --- Typography on glass --- */
  --glass-text: rgba(0, 0, 0, 0.85);
  --glass-text-dark: rgba(255, 255, 255, 0.9);
  --glass-text-muted: rgba(0, 0, 0, 0.5);
  --glass-text-muted-dark: rgba(255, 255, 255, 0.5);

  /* --- Active/hover states --- */
  --glass-hover: rgba(255, 255, 255, 0.25);
  --glass-active: rgba(255, 255, 255, 0.35);
  --glass-hover-dark: rgba(255, 255, 255, 0.1);
  --glass-active-dark: rgba(255, 255, 255, 0.18);

  /* --- Accent (override per-project) --- */
  --accent: #007AFF;
  --accent-glass: rgba(0, 122, 255, 0.15);

  /* --- Transitions --- */
  --glass-transition: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  --glass-transition-slow: 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@media (prefers-color-scheme: dark) {
  :root {
    --glass-bg: var(--glass-bg-dark);
    --glass-border: var(--glass-border-dark);
    --glass-text: var(--glass-text-dark);
    --glass-text-muted: var(--glass-text-muted-dark);
    --glass-hover: var(--glass-hover-dark);
    --glass-active: var(--glass-active-dark);
    --glass-shadow: 0 2px 16px rgba(0, 0, 0, 0.25);
    --glass-shadow-elevated: 0 8px 32px rgba(0, 0, 0, 0.35);
  }
}

@media (prefers-reduced-transparency) {
  :root {
    --glass-bg-light: rgba(245, 245, 247, 0.95);
    --glass-bg-dark: rgba(30, 30, 32, 0.95);
    --glass-bg: var(--glass-bg-light);
    --blur-standard: 0px;
    --blur-heavy: 0px;
    --blur-subtle: 0px;
    --blur-scroll-boost: 0px;
  }
}
```

## Responsive breakpoints

| Name     | Width    | Navbar behavior                              |
|----------|----------|----------------------------------------------|
| mobile   | < 640px  | Bottom tab bar, hamburger menu for overflow   |
| tablet   | 640–1024px | Top floating bar, may collapse to icons     |
| desktop  | > 1024px | Full top floating bar with text labels        |

## Glass mixin (plain CSS)

```css
.glass {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur-standard));
  -webkit-backdrop-filter: blur(var(--blur-standard));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-outer);
  box-shadow: var(--glass-shadow);
  transition: background var(--glass-transition),
              backdrop-filter var(--glass-transition);
}

.glass-pill {
  composes: glass;  /* or just copy the properties */
  border-radius: var(--radius-full);
  padding: var(--glass-padding);
  display: inline-flex;
  align-items: center;
  gap: var(--glass-gap);
}

.glass-pill__item {
  padding: var(--glass-item-padding);
  border-radius: var(--radius-control);
  color: var(--glass-text);
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 500;
  transition: background var(--glass-transition);
  white-space: nowrap;
}

.glass-pill__item:hover {
  background: var(--glass-hover);
}

.glass-pill__item--active {
  background: var(--glass-active);
}
```

## Scroll-edge enhancement (JS)

```js
const glassBar = document.querySelector('.glass-navbar');
let lastScroll = 0;

window.addEventListener('scroll', () => {
  const scrollY = window.scrollY;
  const opacity = Math.min(0.35, 0.18 + scrollY / 1000);
  const blur = Math.min(28, 20 + scrollY / 100);
  
  glassBar.style.setProperty('--glass-bg',
    `rgba(255, 255, 255, ${opacity})`);
  glassBar.style.backdropFilter = `blur(${blur}px)`;
  glassBar.style.webkitBackdropFilter = `blur(${blur}px)`;
  
  lastScroll = scrollY;
}, { passive: true });
```

## Concentric radius calculator

When nesting glass elements, compute inner radius:

```
inner_radius = outer_radius - padding_between
```

Example: glass navbar has `border-radius: 24px` and `padding: 8px`. Each pill inside uses `border-radius: 16px` (24 - 8). Buttons inside pills use `12px` (16 - 4 gap).

## Z-index layers

| Layer             | z-index |
|-------------------|---------|
| Page content      | 0       |
| Sticky headers    | 10      |
| Glass navbar      | 100     |
| Glass bottom bar  | 100     |
| Dropdown/popover  | 200     |
| Modal backdrop    | 300     |
| Modal content     | 310     |
| Toast / snackbar  | 400     |
