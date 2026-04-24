import React, { useState } from 'react'
import './Chat.css'

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
    <div className="chat-container">
      <div className="messages">
        {messages.map((m, i) => (
          <div key={i} className={`message ${m.sender.toLowerCase()}`}>
            <span className="text">{m.text}</span>
          </div>
        ))}
      </div>
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
          disabled={isStreaming}
        />
        <button onClick={handleSend} disabled={isStreaming}>
          Send
        </button>
      </div>
    </div>
  )
}

export default Chat
