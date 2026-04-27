import React from 'react'
import Chat from '../components/Chat/Chat'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const ChatPage: React.FC = () => {
  return (
    <div className="mx-auto max-w-4xl h-[calc(100vh-3rem)]">
      <Card className="flex h-full flex-col">
        <CardHeader>
          <CardTitle>Chat Assistant</CardTitle>
        </CardHeader>
        <CardContent className="flex-1 min-h-0">
          <Chat />
        </CardContent>
      </Card>
    </div>
  )
}

export default ChatPage
