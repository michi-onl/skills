# Liquid Glass — Bootstrap

Bootstrap's navbar component fights glass styling. Override it surgically rather than building from scratch.

## Override Bootstrap navbar

```html
<nav class="navbar navbar-expand-md fixed-top glass-navbar-bs" role="navigation">
  <div class="container-fluid glass-navbar__inner-bs">
    <!-- Identity pill -->
    <div class="glass-pill">
      <a class="glass-pill__item" href="/">MySite</a>
    </div>

    <!-- Mobile toggler (replaces Bootstrap's default) -->
    <button class="glass-pill d-md-none" data-bs-toggle="collapse"
            data-bs-target="#navContent" aria-label="Toggle navigation">
      <span class="glass-pill__item">☰</span>
    </button>

    <!-- Nav pills (desktop) -->
    <div class="collapse navbar-collapse justify-content-center" id="navContent">
      <div class="glass-pill d-none d-md-flex">
        <a class="glass-pill__item" href="/about">About</a>
        <a class="glass-pill__item" href="/projects">Projects</a>
        <a class="glass-pill__item" href="/blog">Blog</a>
      </div>
    </div>

    <!-- Action pill -->
    <div class="glass-pill">
      <button class="glass-pill__item" aria-label="Search">🔍</button>
    </div>
  </div>
</nav>

<!-- Mobile bottom bar (not Bootstrap, custom) -->
<nav class="glass-bottombar d-md-none" role="navigation" aria-label="Mobile navigation">
  <div class="glass-pill glass-bottombar__pill">
    <a href="/" class="glass-pill__item">🏠</a>
    <a href="/projects" class="glass-pill__item">📁</a>
    <a href="/blog" class="glass-pill__item">📝</a>
    <button class="glass-pill__item">🔍</button>
  </div>
</nav>
```

## CSS overrides

```css
/* Kill Bootstrap's default navbar styling */
.glass-navbar-bs {
  background: none !important;
  border: none !important;
  box-shadow: none !important;
  padding: var(--glass-float-margin);
}

.glass-navbar__inner-bs {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur-standard));
  -webkit-backdrop-filter: blur(var(--blur-standard));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  box-shadow: var(--glass-shadow);
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  max-width: min(90vw, 900px);
  margin: 0 auto;
}

/* Override Bootstrap's collapse to work as mobile menu, not inline */
@media (max-width: 767.98px) {
  .navbar-collapse {
    position: fixed;
    top: 70px;
    left: var(--glass-float-margin);
    right: var(--glass-float-margin);
    background: var(--glass-bg);
    backdrop-filter: blur(var(--blur-heavy));
    -webkit-backdrop-filter: blur(var(--blur-heavy));
    border: 1px solid var(--glass-border);
    border-radius: var(--radius-outer);
    padding: 16px;
    box-shadow: var(--glass-shadow-elevated);
  }

  .navbar-collapse .glass-pill {
    display: flex;
    flex-direction: column;
    width: 100%;
  }

  .navbar-collapse .glass-pill__item {
    width: 100%;
    text-align: left;
    padding: 12px 16px;
  }
}
```

## Bootstrap grid with glass

For card layouts, use Bootstrap's grid but don't apply glass to cards:

```html
<div class="row g-4">
  <div class="col-md-4">
    <div class="card" style="border-radius: var(--radius-outer);">
      <!-- solid card, not glass -->
    </div>
  </div>
</div>
```

Glass stays on the navbar and optional floating actions only.

## Bootstrap variables to override

In your SCSS before importing Bootstrap:

```scss
$navbar-padding-y: 0;
$navbar-padding-x: 0;
$nav-link-padding-x: 0;
$nav-link-padding-y: 0;
$border-radius: 24px;
$border-radius-lg: 24px;
```

This prevents Bootstrap's defaults from fighting the glass radii.
