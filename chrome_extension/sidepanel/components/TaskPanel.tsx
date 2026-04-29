import React, { useState, useEffect } from 'react'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CheckCircle2, Circle, Clock, Trash2 } from 'lucide-react'
import type { Task } from '@/types'
import { getTasks, createTask } from '@/lib/api'
import { deleteLocalTask, updateLocalTask, getSettings } from '@/lib/storage'

const TaskPanel: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [newTaskInput, setNewTaskInput] = useState('')

  const loadTasks = async () => {
    setLoading(true)
    try {
      const data = await getTasks()
      setTasks(data)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadTasks()
  }, [])

  const handleAddTask = async () => {
    if (!newTaskInput.trim()) return
    try {
      const task = await createTask(newTaskInput)
      if (task) {
        setTasks((prev) => [task, ...prev])
        setNewTaskInput('')
      }
    } catch {
      // ignore
    }
  }

  const handleDelete = async (taskId: string) => {
    const settings = await getSettings()
    if (settings.mode === 'non_backend') {
      await deleteLocalTask(taskId)
      setTasks((prev) => prev.filter((t) => t.id !== taskId))
    }
    // For backend mode, delete not implemented in API yet
  }

  const handleStatusChange = async (task: Task) => {
    const settings = await getSettings()
    const nextStatus: Task['status'] =
      task.status === 'TODO' ? 'WORKING' : task.status === 'WORKING' ? 'DONE' : 'TODO'
    const updated = { ...task, status: nextStatus }

    if (settings.mode === 'non_backend') {
      await updateLocalTask(updated)
      setTasks((prev) => prev.map((t) => (t.id === task.id ? updated : t)))
    }
    // For backend mode, update not implemented in API yet
  }

  const statusIcon = (status: Task['status']) => {
    switch (status) {
      case 'DONE':
        return <CheckCircle2 className="h-4 w-4 text-green-500" />
      case 'WORKING':
        return <Clock className="h-4 w-4 text-amber-500" />
      default:
        return <Circle className="h-4 w-4 text-muted-foreground" />
    }
  }

  const statusVariant = (status: Task['status']) => {
    switch (status) {
      case 'DONE':
        return 'default'
      case 'WORKING':
        return 'secondary'
      default:
        return 'outline'
    }
  }

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex gap-2">
        <input
          value={newTaskInput}
          onChange={(e) => setNewTaskInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
          placeholder="Add a new task..."
          className="flex h-10 flex-1 rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
        />
        <button
          onClick={handleAddTask}
          className="inline-flex h-10 items-center justify-center rounded-md bg-primary px-4 text-sm font-medium text-primary-foreground hover:bg-primary/90"
        >
          Add
        </button>
      </div>
      <ScrollArea className="flex-1">
        <div className="space-y-2">
          {loading && (
            <p className="text-sm text-muted-foreground">Loading tasks...</p>
          )}
          {!loading && tasks.length === 0 && (
            <p className="text-sm text-muted-foreground">No tasks yet.</p>
          )}
          {tasks.map((task) => (
            <Card key={task.id} className="cursor-pointer hover:bg-accent/50">
              <CardHeader className="p-3 pb-0">
                <div className="flex items-start justify-between">
                  <CardTitle className="text-sm font-medium">
                    {task.title}
                  </CardTitle>
                  <button
                    onClick={() => handleDelete(task.id)}
                    className="text-muted-foreground hover:text-destructive"
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </div>
              </CardHeader>
              <CardContent className="p-3 pt-1">
                {task.description && (
                  <p className="mb-2 text-xs text-muted-foreground line-clamp-2">
                    {task.description}
                  </p>
                )}
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleStatusChange(task)}
                    className="flex items-center gap-1"
                  >
                    {statusIcon(task.status)}
                  </button>
                  <Badge variant={statusVariant(task.status)} className="text-[10px]">
                    {task.status}
                  </Badge>
                  {task.due_date && (
                    <span className="ml-auto text-[10px] text-muted-foreground">
                      {new Date(task.due_date).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </ScrollArea>
    </div>
  )
}

export default TaskPanel
