import React, { useState, useEffect, useRef, useCallback } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Message, ContentBlock, ContentDelta } from '@/types/chat'
import MessageBubble from './MessageBubble'
import ThinkingAnimation from './ThinkingAnimation'

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [hasReceivedFirstToken, setHasReceivedFirstToken] = useState(false)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

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
        if (response.ok) {
          const data = await response.json()
          const history: Message[] = data.map((m: any) => ({
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

  return (
    <div className="flex h-full flex-col">
      <ScrollArea className="flex-1 pr-4">
        <div ref={scrollRef} className="space-y-3">
          {messages.map((m, i) => (
            <MessageBubble
              key={i}
              message={m}
              isStreaming={isStreaming}
              isLast={i === messages.length - 1}
            />
          ))}
        </div>
      </ScrollArea>

      {/* Global thinking indicator */}
      {showGlobalThinking && (
        <div className="flex items-center justify-center py-2">
          <ThinkingAnimation />
        </div>
      )}

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

/**
 * Apply a streaming delta to the current content blocks.
 */
function applyDelta(blocks: ContentBlock[], delta: ContentDelta): ContentBlock[] {
  const next = [...blocks]

  switch (delta.type) {
    case 'text': {
      const last = next[next.length - 1]
      if (last && last.type === 'text') {
        next[next.length - 1] = { ...last, text: last.text + delta.delta }
      } else {
        next.push({ type: 'text', text: delta.delta })
      }
      break
    }
    case 'thinking': {
      const last = next[next.length - 1]
      if (last && last.type === 'thinking') {
        next[next.length - 1] = { ...last, thinking: last.thinking + delta.delta }
      } else {
        next.push({ type: 'thinking', thinking: delta.delta })
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
        name: delta.name || 'tool',
        input: delta.input || {},
      })
      break
    }
    case 'tool_result': {
      next.push({
        type: 'tool_result',
        name: delta.name || 'tool',
        output: delta.output || '',
      })
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
          return `\n[Result: ${b.output}]\n`
        default:
          return ''
      }
    })
    .join('')
}

export default Chat
