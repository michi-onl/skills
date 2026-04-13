# Liquid Glass — shadcn/ui

shadcn gives you unstyled primitives. Layer glass tokens on top without fighting the component API.

## Strategy

Don't wrap shadcn components in glass containers. Instead, apply glass styles directly to shadcn's underlying elements via `className`. The pill-grouping pattern sits *outside* shadcn — it's layout, not component behavior.

## Glass Navbar with shadcn Button

```tsx
import { Button } from '@/components/ui/button';
import Link from 'next/link';

export function GlassNavbar() {
  return (
    <nav className="fixed top-4 left-1/2 -translate-x-1/2 z-50 max-w-[min(90vw,900px)]">
      <div className="flex items-center gap-3 p-1.5 glass-pill-outer">
        {/* Identity pill */}
        <div className="glass-pill">
          <Button variant="ghost" className="glass-pill__item" asChild>
            <Link href="/">Home</Link>
          </Button>
        </div>

        {/* Nav pill */}
        <div className="glass-pill hidden sm:flex">
          <Button variant="ghost" className="glass-pill__item" asChild>
            <Link href="/about">About</Link>
          </Button>
          <Button variant="ghost" className="glass-pill__item" asChild>
            <Link href="/projects">Projects</Link>
          </Button>
          <Button variant="ghost" className="glass-pill__item" asChild>
            <Link href="/blog">Blog</Link>
          </Button>
        </div>

        {/* Action pill */}
        <div className="glass-pill">
          <Button variant="ghost" size="icon" className="glass-pill__item">
            <SearchIcon className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </nav>
  );
}
```

## CSS layer

Add a `glass.css` that your layout imports. Don't put glass styles in Tailwind `@apply` chains — it gets unreadable fast. Use actual CSS classes for the glass surface and Tailwind for spacing/layout.

```css
/* glass.css */
.glass-pill-outer {
  background: var(--glass-bg);
  backdrop-filter: blur(var(--blur-standard));
  -webkit-backdrop-filter: blur(var(--blur-standard));
  border: 1px solid var(--glass-border);
  border-radius: var(--radius-full);
  box-shadow: var(--glass-shadow);
}

.glass-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--glass-gap);
  padding: var(--glass-padding);
  border-radius: var(--radius-full);
}

.glass-pill__item {
  border-radius: var(--radius-control) !important;
  color: var(--glass-text) !important;
  font-weight: 500;
}

.glass-pill__item:hover {
  background: var(--glass-hover) !important;
}
```

The `!important` overrides shadcn's variant styles. This is acceptable here because glass surfaces are a deliberate override of the default button appearance.

## Sheet / Dialog with glass backdrop

shadcn's `Dialog` and `Sheet` accept `overlayClassName`:

```tsx
<Dialog>
  <DialogContent className="border-glass-border bg-glass-light backdrop-blur-glass">
    {/* content */}
  </DialogContent>
</Dialog>
```

Or override the overlay:

```tsx
<DialogOverlay className="bg-black/20 backdrop-blur-[40px]" />
```

## DropdownMenu on glass

```tsx
<DropdownMenuContent className="glass-pill-outer p-2 min-w-[180px]">
  <DropdownMenuItem className="glass-pill__item rounded-xl">
    Profile
  </DropdownMenuItem>
  {/* ... */}
</DropdownMenuContent>
```

## Dark mode

If using `next-themes`, the CSS variables in `design-system.md` handle dark mode via `prefers-color-scheme`. For class-based dark mode, duplicate the dark values under `.dark`:

```css
.dark {
  --glass-bg: var(--glass-bg-dark);
  --glass-border: var(--glass-border-dark);
  --glass-text: var(--glass-text-dark);
  /* etc. */
}
```
