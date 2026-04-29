import React, { useState, useEffect, useRef } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Send, Plus, Loader2 } from 'lucide-react'
import type { Message } from '@/types'
import {
  sendChatMessage,
  getChatHistory,
  createTask,
} from '@/lib/api'
import {
  addLocalMessage,
  setSelectedText,
  getSelectedText,
} from '@/lib/storage'

const ChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    loadHistory()
    checkSelectedText()
  }, [])

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const loadHistory = async () => {
    try {
      const history = await getChatHistory()
      setMessages(history)
    } catch {
      // ignore
    }
  }

  const checkSelectedText = async () => {
    const selected = await getSelectedText()
    if (selected?.text) {
      const prefill = `From "${selected.title}":\n${selected.text}\n\n`
      setInput(prefill)
      await setSelectedText(null)
    }
  }

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return
    setError(null)

    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: 'USER',
      text: input,
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)

    try {
      const currentHistory = [...messages, userMsg]
      let assistantText = ''

      await sendChatMessage(userMsg.text, currentHistory, (accumulated) => {
        assistantText = accumulated
        setMessages((prev) => {
          const withoutLast = prev.filter((m) => m.sender !== 'ASSISTANT' || m.text !== '')
          const lastAssistant = prev[prev.length - 1]
          if (lastAssistant?.sender === 'ASSISTANT' && lastAssistant.text === '') {
            // Update the placeholder
            const next = [...prev]
            next[next.length - 1] = {
              ...next[next.length - 1],
              text: accumulated,
            }
            return next
          }
          return [
            ...withoutLast,
            {
              id: crypto.randomUUID(),
              sender: 'ASSISTANT',
              text: accumulated,
              timestamp: new Date().toISOString(),
            },
          ]
        })
      })

      // Save assistant message locally for non-backend mode
      const settings = await import('@/lib/storage').then((m) => m.getSettings())
      if (settings.mode === 'non_backend') {
        await addLocalMessage({
          id: crypto.randomUUID(),
          sender: 'ASSISTANT',
          text: assistantText,
          timestamp: new Date().toISOString(),
        })
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Something went wrong'
      setError(msg)
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          sender: 'ASSISTANT',
          text: `Error: ${msg}`,
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setIsStreaming(false)
    }
  }

  const handleAddTask = async (text: string) => {
    try {
      const task = await createTask(text)
      if (task) {
        setMessages((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            sender: 'ASSISTANT',
            text: `Task added: "${task.title}"`,
            timestamp: new Date().toISOString(),
          },
        ])
      }
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Failed to add task'
      setError(msg)
    }
  }

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 px-4 py-2">
        <div ref={scrollRef} className="space-y-3">
          {messages.map((m, i) => (
            <div key={m.id || i} className="group">
              <div
                className={`max-w-[90%] rounded-2xl px-4 py-2 text-sm ${
                  m.sender === 'USER'
                    ? 'ml-auto bg-primary text-primary-foreground'
                    : 'bg-muted text-foreground'
                }`}
              >
                <span className="whitespace-pre-wrap">{m.text}</span>
              </div>
              {m.sender === 'USER' && !isStreaming && (
                <div className="mt-1 flex justify-end opacity-0 transition-opacity group-hover:opacity-100">
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 px-2 text-xs"
                    onClick={() => handleAddTask(m.text)}
                  >
                    <Plus className="mr-1 h-3 w-3" />
                    Add as Task
                  </Button>
                </div>
              )}
            </div>
          ))}
          {isStreaming && messages[messages.length - 1]?.sender === 'USER' && (
            <div className="max-w-[90%] rounded-2xl bg-muted px-4 py-2 text-sm text-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
            </div>
          )}
          {error && (
            <Card className="border-destructive">
              <CardContent className="p-3 text-sm text-destructive">
                {error}
              </CardContent>
            </Card>
          )}
        </div>
      </ScrollArea>
      <div className="border-t bg-background p-3">
        <div className="flex gap-2">
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type a message..."
            disabled={isStreaming}
            className="flex-1"
          />
          <Button onClick={handleSend} disabled={isStreaming} size="icon">
            <Send className="h-4 w-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ChatPanel
