import React from 'react'
import Documents from '../components/Documents/Documents'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const KnowledgeBasePage: React.FC = () => {
  return (
    <div className="mx-auto max-w-4xl">
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Base</CardTitle>
        </CardHeader>
        <CardContent>
          <Documents />
        </CardContent>
      </Card>
    </div>
  )
}

export default KnowledgeBasePage
