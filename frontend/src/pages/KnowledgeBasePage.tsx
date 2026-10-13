import React from 'react'
import Documents from '../components/Documents/Documents'
import Page from '@/components/Layout/Page'

const KnowledgeBasePage: React.FC = () => {
  return (
    <Page
      title="Knowledge Base"
      description="Documents you upload are digested so chat can search them."
      width="max-w-2xl"
    >
      <Documents />
    </Page>
  )
}

export default KnowledgeBasePage
