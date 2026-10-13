import React, { useState, useEffect, useRef } from 'react'
import { Alert, Button, TextArea } from '@heroui/react'
import { ArrowUp, Plus, Loader2 } from 'lucide-react'
import type { Message } from '@/types'
import { sendChatMessage, getChatHistory, createTask } from '@/lib/api'
import { addLocalMessage, setSelectedText, getSelectedText } from '@/lib/storage'

const ChatPanel: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 140)}px`
  }, [input])

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
      <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto px-4 py-3">
        {messages.length === 0 && !isStreaming && (
          <p className="pt-10 text-center text-sm text-muted">
            Ask anything, or select text on a page to send it here.
          </p>
        )}
        {messages.map((m, i) => (
          <div key={m.id || i} className="group">
            <div
              className={
                m.sender === 'USER'
                  ? 'ml-auto w-fit max-w-[90%] rounded-2xl rounded-br-md bg-accent px-3.5 py-2 text-sm text-accent-foreground'
                  : 'text-sm leading-relaxed text-foreground'
              }
            >
              <span className="whitespace-pre-wrap">{m.text}</span>
            </div>
            {m.sender === 'USER' && !isStreaming && (
              <div className="mt-1 flex justify-end opacity-0 transition-opacity focus-within:opacity-100 group-hover:opacity-100">
                <Button size="sm" variant="ghost" onPress={() => handleAddTask(m.text)}>
                  <Plus className="size-3" />
                  Add as task
                </Button>
              </div>
            )}
          </div>
        ))}
        {isStreaming && messages[messages.length - 1]?.sender === 'USER' && (
          <Loader2 className="size-4 animate-spin text-muted" aria-label="Thinking" />
        )}
        {error && (
          <Alert status="danger">
            <Alert.Content>
              <Alert.Description>{error}</Alert.Description>
            </Alert.Content>
          </Alert>
        )}
      </div>
      <div className="border-t border-border p-3">
        <div className="flex items-end gap-2 rounded-2xl border border-border bg-surface p-1.5 focus-within:border-accent">
          <TextArea
            ref={inputRef}
            aria-label="Message"
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Message LifeOS…"
            disabled={isStreaming}
            className="max-h-[140px] min-h-8 flex-1 resize-none border-0 bg-transparent px-2 py-1 shadow-none outline-none focus-visible:ring-0"
          />
          <Button
            isIconOnly
            size="sm"
            aria-label="Send message"
            isDisabled={isStreaming || !input.trim()}
            onPress={handleSend}
            className="shrink-0 rounded-xl"
          >
            <ArrowUp className="size-4" />
          </Button>
        </div>
      </div>
    </div>
  )
}

export default ChatPanel
