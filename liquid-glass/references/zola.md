# Liquid Glass — Zola (Rust SSG)

Zola generates static HTML. Glass effects are pure CSS + minimal JS. No build tools needed beyond Zola itself.

## File structure

```
templates/
  base.html          ← glass navbar + bottom bar here
  partials/
    glass-navbar.html
    glass-bottombar.html
sass/
  _glass.scss        ← design tokens + glass classes
  style.scss         ← imports _glass
static/
  js/
    glass-scroll.js  ← scroll-edge enhancement
```

## base.html

```html
<!DOCTYPE html>
<html lang="{{ lang | default(value='en') }}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <link rel="stylesheet" href="{{ get_url(path='style.css') }}">
  <title>{% block title %}{{ config.title }}{% endblock %}</title>
</head>
<body>
  {% include "partials/glass-navbar.html" %}
  
  <main class="page-content">
    {% block content %}{% endblock %}
  </main>

  {% include "partials/glass-bottombar.html" %}
  <script src="{{ get_url(path='js/glass-scroll.js') }}" defer></script>
</body>
</html>
```

## partials/glass-navbar.html

```html
<nav class="glass-navbar" role="navigation" aria-label="Main">
  <div class="glass-navbar__inner">
    <div class="glass-pill">
      <a href="{{ get_url(path='/') }}" class="glass-pill__item
        {% if current_path == '/' %}glass-pill__item--active{% endif %}">
        {{ config.title }}
      </a>
    </div>

    <div class="glass-pill glass-navbar__primary">
      {% set nav_items = [
        ["About", "/about/"],
        ["Projects", "/projects/"],
        ["Blog", "/blog/"]
      ] %}
      {% for item in nav_items %}
        <a href="{{ get_url(path=item[1]) }}"
           class="glass-pill__item
           {% if current_path is starting_with(item[1]) %}glass-pill__item--active{% endif %}">
          {{ item[0] }}
        </a>
      {% endfor %}
    </div>

    <div class="glass-pill">
      <button class="glass-pill__item" id="theme-toggle" aria-label="Toggle theme">🌓</button>
    </div>
  </div>
</nav>
```

## SCSS tokens

In `sass/_glass.scss`, paste the full CSS custom properties from `design-system.md`, then add the `.glass-pill`, `.glass-navbar`, and `.glass-bottombar` classes from `html.md`.

Zola compiles SCSS natively. Import with:

```scss
// sass/style.scss
@import "glass";
// ... rest of site styles
```

## Active page detection

Zola provides `current_path` in templates. Use `is starting_with` for section matches:

```
{% if current_path is starting_with("/blog") %}glass-pill__item--active{% endif %}
```

## Static JS

Copy the scroll-edge JS from `design-system.md` into `static/js/glass-scroll.js`. No bundler needed.
