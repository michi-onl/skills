# Liquid Glass — Plain HTML/CSS/JS

## Navbar template

```html
<nav class="glass-navbar" role="navigation" aria-label="Main">
  <div class="glass-navbar__inner">
    <!-- Group 1: Identity -->
    <div class="glass-pill">
      <a href="/" class="glass-pill__item glass-pill__item--active" aria-current="page">
        <span class="glass-pill__icon"><!-- SVG logo --></span>
        <span class="glass-pill__label">Home</span>
      </a>
    </div>

    <!-- Group 2: Primary nav (desktop only) -->
    <div class="glass-pill glass-navbar__primary">
      <a href="/about" class="glass-pill__item">About</a>
      <a href="/projects" class="glass-pill__item">Projects</a>
      <a href="/blog" class="glass-pill__item">Blog</a>
    </div>

    <!-- Group 3: Actions -->
    <div class="glass-pill">
      <button class="glass-pill__item" aria-label="Search">
        <!-- search icon SVG -->
      </button>
    </div>
  </div>
</nav>

<!-- Mobile bottom bar -->
<nav class="glass-bottombar" role="navigation" aria-label="Main mobile">
  <div class="glass-pill glass-bottombar__pill">
    <a href="/" class="glass-pill__item" aria-label="Home">🏠</a>
    <a href="/projects" class="glass-pill__item" aria-label="Projects">📁</a>
    <a href="/blog" class="glass-pill__item" aria-label="Blog">📝</a>
    <button class="glass-pill__item" aria-label="Search">🔍</button>
  </div>
</nav>
```

## Layout CSS

```css
/* --- Floating navbar (desktop) --- */
.glass-navbar {
  position: fixed;
  top: var(--glass-float-margin);
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  max-width: min(90vw, 900px);
  width: auto;
}

.glass-navbar__inner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px;
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur-standard));
  -webkit-backdrop-filter: blur(var(--blur-standard));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  box-shadow: var(--glass-shadow);
}

/* --- Bottom bar (mobile) --- */
.glass-bottombar {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 8px var(--glass-float-margin) calc(8px + env(safe-area-inset-bottom));
  z-index: 100;
}

.glass-bottombar__pill {
  display: flex;
  justify-content: space-around;
  padding: 8px 16px;
}

/* --- Responsive switch --- */
@media (max-width: 640px) {
  .glass-navbar__primary { display: none; }
  .glass-bottombar { display: block; }
}

@media (min-width: 641px) {
  .glass-bottombar { display: none; }
}

/* --- Page body offset --- */
body {
  padding-top: 80px; /* clear navbar */
}

@media (max-width: 640px) {
  body {
    padding-top: 20px;
    padding-bottom: 80px; /* clear bottom bar */
  }
}
```

## Floating action pill

For a standalone glass control (theme toggle, scroll-to-top):

```html
<div class="glass-fab" aria-label="Actions">
  <div class="glass-pill">
    <button class="glass-pill__item" aria-label="Toggle dark mode">🌓</button>
  </div>
</div>
```

```css
.glass-fab {
  position: fixed;
  bottom: calc(var(--glass-float-margin) + env(safe-area-inset-bottom));
  right: var(--glass-float-margin);
  z-index: 100;
}

@media (max-width: 640px) {
  .glass-fab {
    bottom: calc(80px + var(--glass-float-margin)); /* above bottom bar */
  }
}
```

## Progressive enhancement

```css
@supports not (backdrop-filter: blur(1px)) {
  .glass-pill,
  .glass-navbar__inner,
  .glass-bottombar__pill {
    background: rgba(245, 245, 247, 0.92);
  }
}

@media (prefers-reduced-motion) {
  .glass-pill__item {
    transition: none;
  }
}
```
