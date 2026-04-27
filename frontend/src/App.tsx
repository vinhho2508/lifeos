import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import ChatPage from './pages/ChatPage'
import TasksPage from './pages/TasksPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import Layout from './components/Layout/Layout'

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
      <div className="min-h-screen bg-background">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/"
            element={
              <ProtectedRoute>
                <Layout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Navigate to="/chat" replace />} />
            <Route path="chat" element={<ChatPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="knowledge-base" element={<KnowledgeBasePage />} />
          </Route>
        </Routes>
      </div>
    </Router>
  )
}

export default App
