import React, { useState, useEffect, useRef, useCallback } from 'react'
import { ArrowUp, Sparkles } from 'lucide-react'
import { Button, TextArea } from '@heroui/react'
import { Message, ContentBlock, ContentDelta } from '@/types/chat'
import { syncBrowserTimezone } from '@/services/settingsApi'
import { handleUnauthorized } from '@/services/api'
import MessageBubble from './MessageBubble'
import ThinkingAnimation from './ThinkingAnimation'

const SUGGESTIONS = [
  'What is on my task board?',
  'Add a task: review the weekly plan',
  'Summarize my uploaded documents',
]

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [hasReceivedFirstToken, setHasReceivedFirstToken] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  // Grow the composer with its content (capped; scrolls beyond that)
  useEffect(() => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [input])

  // Load chat history on mount
  useEffect(() => {
    const loadHistory = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch('/api/chat/history', {
          headers: {
            Authorization: token ? `Bearer ${token}` : '',
          },
        })
        if (response.status === 401) {
          handleUnauthorized()
          return
        }
        if (response.ok) {
          const data = await response.json()
          const history: Message[] = data.map((m: Record<string, unknown>) => ({
            id: m.id,
            sender: m.sender,
            text: m.text,
            content: m.content || [],
            timestamp: m.timestamp,
          }))
          setMessages(history)
        }
      } catch (err) {
        console.error('Failed to load history:', err)
      }
    }
    loadHistory()
    syncBrowserTimezone().catch((err) => console.warn('Timezone sync failed:', err))
  }, [])

  const handleSend = useCallback(async () => {
    if (!input.trim() || isStreaming) return

    const userMsg: Message = {
      sender: 'USER',
      text: input,
      content: [{ type: 'text', text: input }],
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)
    setHasReceivedFirstToken(false)

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

      if (response.status === 401) {
        handleUnauthorized()
        return
      }
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // Add empty assistant message that we'll stream into
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ASSISTANT',
          text: '',
          content: [],
          timestamp: new Date().toISOString(),
        },
      ])

      if (reader) {
        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split('\n')
          // Keep the last partial line in the buffer
          buffer = lines.pop() || ''

          for (const line of lines) {
            if (!line.trim()) continue
            try {
              const delta: ContentDelta = JSON.parse(line)
              setMessages((prev) => {
                const next = [...prev]
                const lastMsg = next[next.length - 1]
                if (lastMsg.sender !== 'ASSISTANT') return next

                const updatedContent = applyDelta(lastMsg.content, delta)
                next[next.length - 1] = {
                  ...lastMsg,
                  content: updatedContent,
                  text: blocksToText(updatedContent),
                }
                return next
              })
              // Mark first token received
              setHasReceivedFirstToken(true)
            } catch (e) {
              console.warn('Failed to parse delta:', line, e)
            }
          }
        }
      }
    } catch (err) {
      console.error('Chat error:', err)
      setMessages((prev) => [
        ...prev,
        {
          sender: 'ASSISTANT',
          text: 'Sorry, something went wrong.',
          content: [{ type: 'text', text: 'Sorry, something went wrong.' }],
          timestamp: new Date().toISOString(),
        },
      ])
    } finally {
      setIsStreaming(false)
      setHasReceivedFirstToken(false)
    }
  }, [input, isStreaming])

  // Determine if we should show the global thinking indicator:
  // streaming is active and no first token yet
  const showGlobalThinking = isStreaming && !hasReceivedFirstToken

  const canSend = input.trim().length > 0 && !isStreaming

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto pr-1">
        {messages.length === 0 && !isStreaming ? (
          <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
            <div className="flex size-10 items-center justify-center rounded-xl bg-accent-soft text-accent-soft-foreground">
              <Sparkles className="size-5" />
            </div>
            <div>
              <p className="font-medium">How can I help today?</p>
              <p className="mt-1 text-sm text-muted">Try one of these to get started.</p>
            </div>
            <div className="flex flex-wrap justify-center gap-2">
              {SUGGESTIONS.map((s) => (
                <Button
                  key={s}
                  size="sm"
                  variant="secondary"
                  onPress={() => {
                    setInput(s)
                    inputRef.current?.focus()
                  }}
                >
                  {s}
                </Button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-5 pb-4">
            {messages.map((m, i) => (
              <MessageBubble
                key={i}
                message={m}
                isStreaming={isStreaming}
                isLast={i === messages.length - 1}
              />
            ))}
            {/* Global thinking indicator: streaming started, no token yet */}
            {showGlobalThinking && <ThinkingAnimation />}
          </div>
        )}
      </div>

      <div className="mt-2 flex items-end gap-2 rounded-2xl border border-border bg-surface p-2 shadow-surface focus-within:border-accent">
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
          className="max-h-[200px] min-h-9 flex-1 resize-none border-0 bg-transparent px-2 py-1.5 shadow-none outline-none focus-visible:ring-0"
        />
        <Button
          isIconOnly
          aria-label="Send message"
          isDisabled={!canSend}
          onPress={handleSend}
          className="shrink-0 rounded-xl"
        >
          <ArrowUp className="size-4" />
        </Button>
      </div>
    </div>
  )
}

/**
 * Apply a streaming delta to the current content blocks.
 */
function applyDelta(blocks: ContentBlock[], delta: ContentDelta): ContentBlock[] {
  const next = [...blocks]

  switch (delta.type) {
    case 'text': {
      const last = next[next.length - 1]
      if (last && last.type === 'text') {
        next[next.length - 1] = { ...last, text: last.text + (delta.delta ?? '') }
      } else {
        next.push({ type: 'text', text: delta.delta ?? '' })
      }
      break
    }
    case 'thinking': {
      const last = next[next.length - 1]
      if (last && last.type === 'thinking') {
        next[next.length - 1] = { ...last, thinking: last.thinking + (delta.delta ?? '') }
      } else {
        next.push({ type: 'thinking', thinking: delta.delta ?? '' })
      }
      break
    }
    case 'image': {
      next.push({
        type: 'image',
        url: delta.url || '',
        alt: delta.alt,
      })
      break
    }
    case 'citation': {
      next.push({
        type: 'citation',
        document_id: delta.document_id || '',
        chunk_text: delta.chunk_text || '',
        source_name: delta.source_name || 'Document',
      })
      break
    }
    case 'tool_call': {
      next.push({
        type: 'tool_call',
        id: delta.id || '',
        name: delta.name || 'tool',
        input: delta.input || {},
      })
      break
    }
    case 'tool_result': {
      // Rendered inside its tool_call's card, matched by id (see MessageBubble).
      next.push({
        type: 'tool_result',
        id: delta.id || '',
        name: delta.name || 'tool',
        status: delta.status || 'ok',
        summary: delta.summary || '',
        output: delta.output ?? null,
      })
      break
    }
    case 'error': {
      next.push({ type: 'error', message: delta.message || 'Something went wrong.' })
      break
    }
    default:
      break
  }

  return next
}

/**
 * Convert content blocks back to plain text for fallback display.
 */
function blocksToText(blocks: ContentBlock[]): string {
  return blocks
    .map((b) => {
      switch (b.type) {
        case 'text':
          return b.text
        case 'thinking':
          return `\n[Thinking: ${b.thinking}]\n`
        case 'image':
          return `\n[Image: ${b.alt || b.url}]\n`
        case 'citation':
          return `\n[Source: ${b.source_name}]\n`
        case 'tool_call':
          return `\n[Tool: ${b.name}]\n`
        case 'tool_result':
          return `\n[Result: ${b.summary}]\n`
        default:
          return ''
      }
    })
    .join('')
}

export default Chat
