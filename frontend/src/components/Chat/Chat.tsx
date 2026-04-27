import React, { useState } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'

interface Message {
  sender: 'USER' | 'ASSISTANT'
  text: string
  timestamp: string
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return

    const userMsg: Message = {
      sender: 'USER',
      text: input,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)

    try {
      const token = localStorage.getItem('token')
      const response = await fetch('/api/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: token ? `Bearer ${token}` : '',
        },
        body: JSON.stringify({ message: input }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let accumulated = ''

      setMessages((prev) => [
        ...prev,
        { sender: 'ASSISTANT', text: '', timestamp: new Date().toISOString() },
      ])

      if (reader) {
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          accumulated += decoder.decode(value, { stream: true })
          setMessages((prev) => {
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              text: accumulated,
            }
            return next
          })
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ASSISTANT',
          text: 'Sorry, something went wrong.',
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setIsStreaming(false)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 pr-4">
        <div className="space-y-3">
          {messages.map((m, i) => (
            <div
              key={i}
              className={`max-w-[80%] rounded-2xl px-4 py-2 ${
                m.sender === 'USER'
                  ? 'ml-auto bg-primary text-primary-foreground'
                  : 'bg-muted text-foreground'
              }`}
            >
              <span className="text-sm whitespace-pre-wrap">{m.text}</span>
            </div>
          ))}
        </div>
      </ScrollArea>
      <div className="mt-4 flex gap-2">
        <Input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
          disabled={isStreaming}
        />
        <Button onClick={handleSend} disabled={isStreaming}>
          Send
        </Button>
      </div>
    </div>
  )
}

export default Chat
