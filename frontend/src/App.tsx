import React from 'react'
import { Toast } from '@heroui/react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import ChatPage from './pages/ChatPage'
import TasksPage from './pages/TasksPage'
import KnowledgeBasePage from './pages/KnowledgeBasePage'
import Layout from './components/Layout/Layout'
import SettingsPage from './pages/SettingsPage'

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
      <div className="min-h-dvh bg-background text-foreground">
        <Toast.Provider />
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
            <Route path="chat/:conversationId?" element={<ChatPage />} />
            <Route path="tasks" element={<TasksPage />} />
            <Route path="knowledge-base" element={<KnowledgeBasePage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </div>
    </Router>
  )
}

export default App
