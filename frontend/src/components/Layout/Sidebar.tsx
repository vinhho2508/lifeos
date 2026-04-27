import React from 'react'
import { NavLink } from 'react-router-dom'
import { MessageSquare, Layout, FileText } from 'lucide-react'
import { ThemeToggle } from '../ThemeToggle'

const navItems = [
  { path: '/chat', label: 'Chat', icon: MessageSquare },
  { path: '/tasks', label: 'Tasks', icon: Layout },
  { path: '/knowledge-base', label: 'Knowledge Base', icon: FileText },
]

const Sidebar: React.FC = () => {
  return (
    <aside className="hidden md:flex w-56 flex-col border-r bg-background">
      <div className="flex h-16 items-center border-b px-4">
        <h1 className="text-lg font-bold tracking-tight">LifeOS</h1>
      </div>
      <nav className="flex-1 space-y-1 p-3">
        {navItems.map(({ path, label, icon: Icon }) => (
          <NavLink
            key={path}
            to={path}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-muted hover:text-foreground'
              }`
            }
          >
            <Icon className="h-4 w-4" />
            {label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t p-3">
        <ThemeToggle />
      </div>
    </aside>
  )
}

export default Sidebar
