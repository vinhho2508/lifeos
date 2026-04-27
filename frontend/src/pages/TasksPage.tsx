import React from 'react'
import Board from '../components/Board/Board'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const TasksPage: React.FC = () => {
  return (
    <div className="mx-auto max-w-6xl">
      <Card>
        <CardHeader>
          <CardTitle>Task Board</CardTitle>
        </CardHeader>
        <CardContent>
          <Board />
        </CardContent>
      </Card>
    </div>
  )
}

export default TasksPage
