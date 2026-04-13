# Liquid Glass — Next.js / React

## Component structure

```
components/
  glass/
    GlassNavbar.tsx
    GlassPill.tsx
    GlassBottomBar.tsx
    GlassFab.tsx
    glass.css          ← import design-system tokens here
```

## GlassPill component

The foundational building block. Every glass surface is a pill or contains pills.

```tsx
import { ReactNode } from 'react';

interface GlassPillProps {
  children: ReactNode;
  className?: string;
  as?: 'div' | 'nav';
}

export function GlassPill({ children, className = '', as: Tag = 'div' }: GlassPillProps) {
  return (
    <Tag className={`glass-pill ${className}`}>
      {children}
    </Tag>
  );
}

interface PillItemProps {
  children: ReactNode;
  href?: string;
  active?: boolean;
  onClick?: () => void;
  ariaLabel?: string;
}

export function PillItem({ children, href, active, onClick, ariaLabel }: PillItemProps) {
  const cls = `glass-pill__item ${active ? 'glass-pill__item--active' : ''}`;

  if (href) {
    // Use Next.js Link in real implementation
    return <a href={href} className={cls} aria-current={active ? 'page' : undefined}>{children}</a>;
  }
  return <button className={cls} onClick={onClick} aria-label={ariaLabel}>{children}</button>;
}
```

## GlassNavbar

```tsx
'use client';

import { useEffect, useState } from 'react';
import { GlassPill, PillItem } from './GlassPill';

export function GlassNavbar() {
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 20);
    window.addEventListener('scroll', onScroll, { passive: true });
    return () => window.removeEventListener('scroll', onScroll);
  }, []);

  return (
    <>
      {/* Desktop navbar */}
      <nav
        className={`glass-navbar ${scrolled ? 'glass-navbar--scrolled' : ''}`}
        role="navigation"
        aria-label="Main"
      >
        <div className="glass-navbar__inner">
          <GlassPill>
            <PillItem href="/" active>Home</PillItem>
          </GlassPill>

          <GlassPill className="glass-navbar__primary">
            <PillItem href="/about">About</PillItem>
            <PillItem href="/projects">Projects</PillItem>
            <PillItem href="/blog">Blog</PillItem>
          </GlassPill>

          <GlassPill>
            <PillItem ariaLabel="Search" onClick={() => {}}>🔍</PillItem>
          </GlassPill>
        </div>
      </nav>

      {/* Mobile bottom bar */}
      <nav className="glass-bottombar" role="navigation" aria-label="Main mobile">
        <GlassPill className="glass-bottombar__pill">
          <PillItem href="/" ariaLabel="Home">🏠</PillItem>
          <PillItem href="/projects" ariaLabel="Projects">📁</PillItem>
          <PillItem href="/blog" ariaLabel="Blog">📝</PillItem>
          <PillItem ariaLabel="Search" onClick={() => {}}>🔍</PillItem>
        </GlassPill>
      </nav>
    </>
  );
}
```

## Scroll-edge hook

```tsx
import { useEffect, useRef } from 'react';

export function useScrollGlass(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const handler = () => {
      const y = window.scrollY;
      const opacity = Math.min(0.35, 0.18 + y / 1000);
      const blur = Math.min(28, 20 + y / 100);
      el.style.setProperty('--glass-bg', `rgba(255,255,255,${opacity})`);
      el.style.backdropFilter = `blur(${blur}px)`;
      (el.style as any).webkitBackdropFilter = `blur(${blur}px)`;
    };

    window.addEventListener('scroll', handler, { passive: true });
    return () => window.removeEventListener('scroll', handler);
  }, [ref]);
}
```

## Tailwind integration

If using Tailwind alongside the design tokens, add to `tailwind.config.ts`:

```ts
export default {
  theme: {
    extend: {
      backdropBlur: {
        glass: '20px',
        'glass-heavy': '40px',
      },
      borderRadius: {
        glass: '24px',
        'glass-inner': '16px',
        'glass-control': '12px',
      },
      colors: {
        glass: {
          light: 'rgba(255, 255, 255, 0.18)',
          dark: 'rgba(0, 0, 0, 0.22)',
          border: 'rgba(255, 255, 255, 0.3)',
        },
      },
    },
  },
};
```

Then you can use classes like `backdrop-blur-glass bg-glass-light border-glass-border rounded-glass`.

## App Router layout pattern

In `app/layout.tsx`, place the navbar outside `{children}` so it persists across routes:

```tsx
import { GlassNavbar } from '@/components/glass/GlassNavbar';
import '@/components/glass/glass.css';

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <GlassNavbar />
        <main className="pt-20 md:pt-24 pb-20 md:pb-0">
          {children}
        </main>
      </body>
    </html>
  );
}
```
