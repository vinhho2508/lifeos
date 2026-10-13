import React, { useState, useEffect } from 'react'
import { Button, Card, Chip, Input, Skeleton } from '@heroui/react'
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
        return <CheckCircle2 className="size-4 text-success" />
      case 'WORKING':
        return <Clock className="size-4 text-warning" />
      default:
        return <Circle className="size-4 text-muted" />
    }
  }

  const statusLabel: Record<Task['status'], string> = {
    TODO: 'To do',
    WORKING: 'In progress',
    DONE: 'Done',
  }
  const statusColor: Record<Task['status'], 'default' | 'warning' | 'success'> = {
    TODO: 'default',
    WORKING: 'warning',
    DONE: 'success',
  }

  return (
    <div className="flex h-full flex-col p-4">
      <div className="mb-4 flex gap-2">
        <Input
          fullWidth
          aria-label="New task"
          value={newTaskInput}
          onChange={(e) => setNewTaskInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
          placeholder="Add a new task…"
        />
        <Button isDisabled={!newTaskInput.trim()} onPress={handleAddTask}>
          Add
        </Button>
      </div>
      <div className="flex-1 space-y-2 overflow-y-auto">
        {loading && (
          <>
            <Skeleton className="h-16 w-full rounded-xl" />
            <Skeleton className="h-16 w-full rounded-xl" />
          </>
        )}
        {!loading && tasks.length === 0 && <p className="text-sm text-muted">No tasks yet.</p>}
        {tasks.map((task) => (
          <Card key={task.id} className="gap-2 p-3">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-snug">{task.title}</p>
              <Button
                isIconOnly
                size="sm"
                variant="ghost"
                aria-label={`Delete ${task.title}`}
                onPress={() => handleDelete(task.id)}
              >
                <Trash2 className="size-3.5" />
              </Button>
            </div>
            {task.description && (
              <p className="line-clamp-2 text-xs text-muted">{task.description}</p>
            )}
            <div className="flex items-center gap-2">
              <button
                onClick={() => handleStatusChange(task)}
                aria-label={`Status: ${statusLabel[task.status]}. Click to advance.`}
                className="flex items-center gap-1 rounded-md"
              >
                {statusIcon(task.status)}
              </button>
              <Chip size="sm" color={statusColor[task.status]} variant="soft">
                {statusLabel[task.status]}
              </Chip>
              {task.due_date && (
                <span className="ml-auto text-[11px] text-muted">
                  {new Date(task.due_date).toLocaleDateString()}
                </span>
              )}
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}

export default TaskPanel
