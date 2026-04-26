import React, { useEffect, useState } from 'react'
import api from '../../services/api'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  DndContext,
  DragOverlay,
  closestCorners,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  useDroppable,
  type DragStartEvent,
  type DragEndEvent,
  type DragOverEvent,
} from '@dnd-kit/core'
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'

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

const columns: Task['status'][] = ['TODO', 'WORKING', 'DONE']

function TaskCard({ task, showButtons, onMoveLeft, onMoveRight }: {
  task: Task
  showButtons: { left: boolean; right: boolean }
  onMoveLeft?: () => void
  onMoveRight?: () => void
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: task.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.5 : 1,
  }

  return (
    <Card ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <CardContent className="p-3 cursor-grab active:cursor-grabbing">
        <p className="text-sm mb-2">{task.title}</p>
        <div className="flex justify-between" onClick={(e) => e.stopPropagation()}>
          {showButtons.left && onMoveLeft && (
            <Button variant="ghost" size="sm" onClick={onMoveLeft}>
              ←
            </Button>
          )}
          {showButtons.right && onMoveRight && (
            <Button variant="ghost" size="sm" onClick={onMoveRight}>
              →
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function SortableColumn({ status, tasks, onMoveTask }: {
  status: Task['status']
  tasks: Task[]
  onMoveTask: (id: string, newStatus: Task['status']) => void
}) {
  const colIndex = columns.indexOf(status)
  const { setNodeRef } = useDroppable({ id: status })

  return (
    <div className="w-64 shrink-0">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="font-semibold text-sm">{status}</h3>
        <Badge variant={statusColors[status]}>
          {tasks.length}
        </Badge>
      </div>
      <SortableContext id={status} items={tasks.map((t) => t.id)} strategy={verticalListSortingStrategy}>
        <div ref={setNodeRef} className="space-y-2 min-h-[200px] rounded-lg border border-dashed border-muted-foreground/25 bg-muted/30 p-2 transition-colors">
          {tasks.map((t) => (
            <TaskCard
              key={t.id}
              task={t}
              showButtons={{ left: colIndex > 0, right: colIndex < columns.length - 1 }}
              onMoveLeft={colIndex > 0 ? () => onMoveTask(t.id, columns[colIndex - 1]) : undefined}
              onMoveRight={colIndex < columns.length - 1 ? () => onMoveTask(t.id, columns[colIndex + 1]) : undefined}
            />
          ))}
        </div>
      </SortableContext>
    </div>
  )
}

const Board: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([])
  const [activeId, setActiveId] = useState<string | null>(null)
  const [originalStatus, setOriginalStatus] = useState<Task['status'] | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates })
  )

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
    const prev = tasks
    setTasks((old) => old.map((t) => (t.id === id ? { ...t, status: newStatus } : t)))
    try {
      await api.put(`/tasks/${id}`, { status: newStatus })
    } catch (err) {
      console.error('Move task error:', err)
      setTasks(prev)
    }
  }

  const handleDragStart = (event: DragStartEvent) => {
    const id = String(event.active.id)
    setActiveId(id)
    const task = tasks.find((t) => t.id === id)
    if (task) setOriginalStatus(task.status)
  }

  const handleDragOver = (event: DragOverEvent) => {
    const { active, over } = event
    if (!over) return

    const activeTask = tasks.find((t) => t.id === active.id)
    if (!activeTask) return

    const overId = String(over.id)
    const overStatus = columns.find((c) => c === overId)
    const overTask = tasks.find((t) => t.id === overId)

    let newStatus: Task['status'] | null = null
    if (overStatus) {
      newStatus = overStatus
    } else if (overTask) {
      newStatus = overTask.status
    }

    if (newStatus && newStatus !== activeTask.status) {
      setTasks((old) =>
        old.map((t) => (t.id === activeTask.id ? { ...t, status: newStatus! } : t))
      )
    }
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveId(null)

    if (!over) return

    const activeTask = tasks.find((t) => t.id === active.id)
    if (!activeTask) return

    const overId = String(over.id)

    let targetStatus: Task['status'] | null = null
    if (columns.includes(overId as Task['status'])) {
      targetStatus = overId as Task['status']
    } else {
      const overTask = tasks.find((t) => t.id === overId)
      if (overTask) {
        targetStatus = overTask.status
      }
    }

    if (targetStatus && originalStatus !== targetStatus) {
      moveTask(activeTask.id, targetStatus)
    }
    setOriginalStatus(null)
  }

  const activeTask = activeId ? tasks.find((t) => t.id === activeId) : null

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCorners}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4">
        {columns.map((col) => (
          <SortableColumn
            key={col}
            status={col}
            tasks={tasks.filter((t) => t.status === col)}
            onMoveTask={moveTask}
          />
        ))}
      </div>
      <DragOverlay>
        {activeTask ? (
          <Card className="w-60 rotate-3 shadow-lg">
            <CardContent className="p-3">
              <p className="text-sm">{activeTask.title}</p>
            </CardContent>
          </Card>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}

export default Board