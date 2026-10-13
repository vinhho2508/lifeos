import React from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { MobileTabBar, MobileTopBar } from './MobileNav'

const Layout: React.FC = () => {
  return (
    <div className="flex h-dvh flex-col bg-background text-foreground md:flex-row">
      <Sidebar />
      <MobileTopBar />
      <main className="flex min-h-0 flex-1 flex-col overflow-y-auto">
        <Outlet />
      </main>
      <MobileTabBar />
    </div>
  )
}

export default Layout
