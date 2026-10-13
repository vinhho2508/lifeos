import React, { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { History } from 'lucide-react'
import Chat from '../components/Chat/Chat'
import ConversationList from '../components/Chat/ConversationList'
import Page from '@/components/Layout/Page'

const ChatPage: React.FC = () => {
  const { conversationId } = useParams<{ conversationId?: string }>()
  const navigate = useNavigate()
  const [refreshKey, setRefreshKey] = useState(0)
  const [chatKey, setChatKey] = useState(0)
  const [showList, setShowList] = useState(false)
  // A conversation the open Chat just created: navigating to it must not remount (and
  // so interrupt) the stream that is about to start.
  const createdRef = useRef<string | null>(null)

  useEffect(() => {
    if (conversationId && conversationId === createdRef.current) return
    createdRef.current = null
    setChatKey((k) => k + 1)
  }, [conversationId])

  const onCreated = useCallback(
    (id: string) => {
      createdRef.current = id
      navigate(`/chat/${id}`, { replace: true })
    },
    [navigate],
  )
  const onTurnComplete = useCallback(() => setRefreshKey((k) => k + 1), [])
  const open = (path: string) => {
    setShowList(false)
    navigate(path)
  }

  return (
    <Page
      title="Chat"
      description="Ask anything, or have LifeOS manage your tasks and notes."
      width="max-w-5xl"
      fill
      actions={
        <button
          type="button"
          aria-label="Conversations"
          onClick={() => setShowList((v) => !v)}
          className="flex size-8 items-center justify-center rounded-md border border-border md:hidden"
        >
          <History className="size-4" />
        </button>
      }
    >
      <div className="flex min-h-0 flex-1 gap-6">
        <aside
          className={`${showList ? 'flex' : 'hidden'} w-full shrink-0 flex-col md:flex md:w-56`}
        >
          <ConversationList
            activeId={conversationId}
            refreshKey={refreshKey}
            onSelect={(id) => open(`/chat/${id}`)}
            onNew={() => open('/chat')}
            onDeletedActive={() => open('/chat')}
          />
        </aside>
        <div className={`${showList ? 'hidden' : 'flex'} min-h-0 min-w-0 flex-1 flex-col md:flex`}>
          <Chat
            key={chatKey}
            conversationId={conversationId}
            onConversationCreated={onCreated}
            onTurnComplete={onTurnComplete}
          />
        </div>
      </div>
    </Page>
  )
}

export default ChatPage
