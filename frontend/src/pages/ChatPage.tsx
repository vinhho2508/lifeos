import React from 'react'
import Chat from '../components/Chat/Chat'
import Page from '@/components/Layout/Page'

const ChatPage: React.FC = () => {
  return (
    <Page
      title="Chat"
      description="Ask anything, or have LifeOS manage your tasks and notes."
      width="max-w-3xl"
      fill
    >
      <Chat />
    </Page>
  )
}

export default ChatPage
