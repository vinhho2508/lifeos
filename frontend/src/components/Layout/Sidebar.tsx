import React from 'react'
import { NavLink } from 'react-router-dom'
import { ThemeToggle } from '../ThemeToggle'
import { navItems } from './navItems'

const Sidebar: React.FC = () => {
  return (
    <aside className="hidden w-60 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-14 items-center gap-2 px-4">
        <div className="flex size-6 items-center justify-center rounded-md bg-accent text-xs font-semibold text-accent-foreground">
          L
        </div>
        <span className="text-sm font-semibold tracking-tight">LifeOS</span>
      </div>
      <nav className="flex-1 space-y-0.5 px-2 py-2" aria-label="Main">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-2.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-accent-soft text-accent-soft-foreground'
                  : 'text-muted hover:bg-surface-secondary hover:text-foreground'
              }`
            }
          >
            <Icon className="size-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="flex items-center justify-between border-t border-border px-3 py-2">
        <span className="text-xs text-muted">Theme</span>
        <ThemeToggle />
      </div>
    </aside>
  )
}

export default Sidebar
