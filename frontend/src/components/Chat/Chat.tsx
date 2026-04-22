import React, { useState, useEffect } from 'react'
import api from '../../services/api'
import './Chat.css'

interface Message {
  sender: 'USER' | 'ASSISTANT'
  text: str
  timestamp: string
}

const Chat: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')

  const handleSend = async () => {
    if (!input.trim()) return

    const userMsg: Message = { sender: 'USER', text: input, timestamp: new Date().toISOString() }
    setMessages([...messages, userMsg])
    setInput('')

    try {
      const res = await api.post('/chat', { message: input })
      const assistantMsg: Message = { sender: 'ASSISTANT', text: res.data.reply, timestamp: new Date().toISOString() }
      setMessages((prev) => [...prev, assistantMsg])
    } catch (err) {
      console.error('Chat error:', err)
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
          onKeyPress={(e) => e.key === 'Enter' && handleSend()}
          placeholder="Type a message..."
        />
        <button onClick={handleSend}>Send</button>
      </div>
    </div>
  )
}

export default Chat
