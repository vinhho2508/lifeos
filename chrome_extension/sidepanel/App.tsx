import React, { useState, useEffect } from 'react'
import { MessageSquare, ListTodo } from 'lucide-react'
import ChatPanel from './components/ChatPanel.tsx'
import TaskPanel from './components/TaskPanel.tsx'
import ModeBadge from './components/ModeBadge.tsx'
import { getSettings } from '@/lib/storage'
import type { ExtensionMode } from '@/types'

type Tab = 'chat' | 'tasks'

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<Tab>('chat')
  const [mode, setMode] = useState<ExtensionMode>('with_backend')

  useEffect(() => {
    getSettings().then((s) => setMode(s.mode))

    // Listen for storage changes to update mode in real-time
    const listener = (changes: Record<string, chrome.storage.StorageChange>) => {
      if (changes.lifeos_settings) {
        setMode(changes.lifeos_settings.newValue.mode)
      }
    }
    chrome.storage.local.onChanged.addListener(listener)
    return () => chrome.storage.local.onChanged.removeListener(listener)
  }, [])

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Header */}
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="text-base font-semibold">LifeOS</span>
          <ModeBadge mode={mode} />
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b">
        <button
          onClick={() => setActiveTab('chat')}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'chat'
              ? 'border-b-2 border-primary text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <MessageSquare className="h-4 w-4" />
          Chat
        </button>
        <button
          onClick={() => setActiveTab('tasks')}
          className={`flex flex-1 items-center justify-center gap-1.5 py-2.5 text-sm font-medium transition-colors ${
            activeTab === 'tasks'
              ? 'border-b-2 border-primary text-primary'
              : 'text-muted-foreground hover:text-foreground'
          }`}
        >
          <ListTodo className="h-4 w-4" />
          Tasks
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {activeTab === 'chat' ? <ChatPanel /> : <TaskPanel />}
      </div>
    </div>
  )
}

export default App
