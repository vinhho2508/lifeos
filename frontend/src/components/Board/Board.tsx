import React, { useEffect, useState } from 'react'
import api from '../../services/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface Task {
  id: string
  title: string
  status: 'TODO' | 'WORKING' | 'DONE'
}

const statusColors: Record<Task['status'], 'default' | 'secondary' | 'destructive'> = {
  TODO: 'default',
  WORKING: 'secondary',
  DONE: 'destructive',
}

const Board: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])

  const fetchTasks = async () => {
    try {
      const res = await api.get('/tasks')
      setTasks(res.data)
    } catch (err) {
      console.error('Fetch tasks error:', err)
    }
  }

  useEffect(() => {
    fetchTasks()
  }, [])

  const moveTask = async (id: string, newStatus: Task['status']) => {
    try {
      await api.put(`/tasks/${id}`, { status: newStatus })
      setTasks((prev) =>
        prev.map((t) => (t.id === id ? { ...t, status: newStatus } : t))
      )
    } catch (err) {
      console.error('Move task error:', err)
    }
  }

  const columns: Task['status'][] = ['TODO', 'WORKING', 'DONE']

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {columns.map((col) => (
        <div key={col} className="w-64 shrink-0">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="font-semibold text-sm">{col}</h3>
            <Badge variant={statusColors[col]}>
              {tasks.filter((t) => t.status === col).length}
            </Badge>
          </div>
          <div className="space-y-2">
            {tasks
              .filter((t) => t.status === col)
              .map((t) => (
                <Card key={t.id}>
                  <CardContent className="p-3">
                    <p className="text-sm mb-2">{t.title}</p>
                    <div className="flex justify-between">
                      {col !== 'TODO' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => moveTask(t.id, columns[columns.indexOf(col) - 1])}
                        >
                          ←
                        </Button>
                      )}
                      {col !== 'DONE' && (
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => moveTask(t.id, columns[columns.indexOf(col) + 1])}
                        >
                          →
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default Board
