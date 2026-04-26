import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Login from './pages/Login'
import Chat from './components/Chat/Chat'
import Board from './components/Board/Board'
import Documents from './components/Documents/Documents'
import { ThemeToggle } from './components/ThemeToggle'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const Home: React.FC = () => {
  return (
    <div className="min-h-screen bg-background p-6">
      <div className="mx-auto max-w-7xl">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-3xl font-bold tracking-tight">LifeOS Assistant Dashboard</h1>
          <ThemeToggle />
        </div>
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[450px_1fr] lg:grid-rows-2">
          <Card className="lg:row-span-2">
            <CardHeader>
              <CardTitle>Chat Assistant</CardTitle>
            </CardHeader>
            <CardContent>
              <Chat />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Task Board</CardTitle>
            </CardHeader>
            <CardContent>
              <Board />
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle>Knowledge Base</CardTitle>
            </CardHeader>
            <CardContent>
              <Documents />
            </CardContent>
          </Card>
        </div>
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
      <div className="min-h-screen bg-background">
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
