import React from 'react'
import Board from '../components/Board/Board'
import Page from '@/components/Layout/Page'

const TasksPage: React.FC = () => {
  return (
    <Page
      title="Tasks"
      description="Drag cards between columns to update their status."
      width="max-w-6xl"
    >
      <Board />
    </Page>
  )
}

export default TasksPage
