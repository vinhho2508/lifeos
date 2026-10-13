import React, { useState, useEffect } from 'react'
import { MessageSquare, ListTodo } from 'lucide-react'
import { Tabs } from '@heroui/react'
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
      <div className="flex items-center gap-2 border-b border-border px-4 py-3">
        <div className="flex size-5 items-center justify-center rounded-md bg-accent text-[11px] font-semibold text-accent-foreground">
          L
        </div>
        <span className="text-sm font-semibold tracking-tight">LifeOS</span>
        <ModeBadge mode={mode} />
      </div>

      <Tabs
        className="flex min-h-0 flex-1 flex-col"
        selectedKey={activeTab}
        onSelectionChange={(key) => setActiveTab(key as Tab)}
      >
        <Tabs.ListContainer className="px-3 py-2">
          <Tabs.List aria-label="Sections">
            <Tabs.Tab id="chat">
              <MessageSquare className="mr-1.5 inline size-4" />
              Chat
              <Tabs.Indicator />
            </Tabs.Tab>
            <Tabs.Tab id="tasks">
              <ListTodo className="mr-1.5 inline size-4" />
              Tasks
              <Tabs.Indicator />
            </Tabs.Tab>
          </Tabs.List>
        </Tabs.ListContainer>
        <Tabs.Panel id="chat" className="min-h-0 flex-1">
          <ChatPanel />
        </Tabs.Panel>
        <Tabs.Panel id="tasks" className="min-h-0 flex-1">
          <TaskPanel />
        </Tabs.Panel>
      </Tabs>
    </div>
  )
}

export default App
