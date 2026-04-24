import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Chat from './components/Chat/Chat'
import Board from './components/Board/Board'
import Documents from './components/Documents/Documents'
import './App.css'

const Home: React.FC = () => {
  return (
    <div className="home-dashboard">
      <h1>LifeOS Assistant Dashboard</h1>
      <div className="dashboard-grid">
        <section className="chat-section">
          <h2>Chat Assistant</h2>
          <Chat />
        </section>
        <section className="board-section">
          <h2>Task Board</h2>
          <Board />
        </section>
        <section className="docs-section">
          <Documents />
        </section>
      </div>
    </div>
  )
}

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const token = localStorage.getItem('token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function App() {
  return (
    <Router>
      <div className="App">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route 
            path="/" 
            element={
              <ProtectedRoute>
                <Home />
              </ProtectedRoute>
            } 
          />
        </Routes>
      </div>
    </Router>
  )
}

export default App
