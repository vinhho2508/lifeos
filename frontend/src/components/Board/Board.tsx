import React, { useEffect, useState } from 'react'
import api from '../../services/api'
import './Board.css'

interface Task {
  id: string
  title: string
  status: 'TODO' | 'WORKING' | 'DONE'
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
    <div className="board">
      {columns.map((col) => (
        <div key={col} className="column">
          <h3>{col}</h3>
          <div className="task-list">
            {tasks
              .filter((t) => t.status === col)
              .map((t) => (
                <div key={t.id} className="task-card">
                  <span>{t.title}</span>
                  <div className="controls">
                    {col !== 'TODO' && <button onClick={() => moveTask(t.id, columns[columns.indexOf(col)-1])}>←</button>}
                    {col !== 'DONE' && <button onClick={() => moveTask(t.id, columns[columns.indexOf(col)+1])}>→</button>}
                  </div>
                </div>
              ))}
          </div>
        </div>
      ))}
    </div>
  )
}

export default Board
