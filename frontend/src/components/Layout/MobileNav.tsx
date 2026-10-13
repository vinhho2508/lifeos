import React from 'react'
import { NavLink } from 'react-router-dom'
import { ThemeToggle } from '../ThemeToggle'
import { navItems } from './navItems'

/** Small-screen chrome: a slim top bar plus a bottom tab bar (the sidebar is desktop-only). */
export const MobileTopBar: React.FC = () => (
  <header className="flex h-12 shrink-0 items-center justify-between border-b border-border bg-surface px-4 md:hidden">
    <div className="flex items-center gap-2">
      <div className="flex size-6 items-center justify-center rounded-md bg-accent text-xs font-semibold text-accent-foreground">
        L
      </div>
      <span className="text-sm font-semibold tracking-tight">LifeOS</span>
    </div>
    <ThemeToggle />
  </header>
)

export const MobileTabBar: React.FC = () => (
  <nav
    aria-label="Main"
    className="grid shrink-0 grid-cols-4 border-t border-border bg-surface pb-[env(safe-area-inset-bottom)] md:hidden"
  >
    {navItems.map(({ path, label, icon: Icon }) => (
      <NavLink
        key={path}
        to={path}
        className={({ isActive }) =>
          `flex flex-col items-center gap-0.5 py-2 text-[11px] font-medium transition-colors ${
            isActive ? 'text-accent' : 'text-muted'
          }`
        }
      >
        <Icon className="size-5" />
        {label}
      </NavLink>
    ))}
  </nav>
)
