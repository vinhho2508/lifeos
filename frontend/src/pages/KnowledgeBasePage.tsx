import React, { useCallback, useEffect, useState } from 'react'
import { toast } from '@heroui/react'
import Documents from '../components/Documents/Documents'
import DocumentList from '../components/Documents/DocumentList'
import Page from '@/components/Layout/Page'
import {
  KnowledgeDocument,
  deleteDocument,
  errorDetail,
  isPending,
  listDocuments,
  reindexDocument,
} from '@/services/documentsApi'

const POLL_MS = 2000

const KnowledgeBasePage: React.FC = () => {
  const [documents, setDocuments] = useState<KnowledgeDocument[] | null>(null)
  const [busyIds, setBusyIds] = useState<Set<string>>(new Set())

  const load = useCallback(async () => {
    try {
      setDocuments(await listDocuments())
    } catch (err) {
      console.error('Failed to load documents', err)
      setDocuments((current) => current ?? [])
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // Poll while anything is still being digested.
  const pending = documents?.some(isPending) ?? false
  useEffect(() => {
    if (!pending) return
    const timer = window.setInterval(load, POLL_MS)
    return () => window.clearInterval(timer)
  }, [pending, load])

  const withBusy = async (id: string, action: () => Promise<void>) => {
    setBusyIds((ids) => new Set(ids).add(id))
    try {
      await action()
    } finally {
      setBusyIds((ids) => {
        const next = new Set(ids)
        next.delete(id)
        return next
      })
    }
  }

  const replace = (doc: KnowledgeDocument) =>
    setDocuments((docs) => (docs ?? []).map((d) => (d.id === doc.id ? doc : d)))

  const handleReindex = (doc: KnowledgeDocument) =>
    withBusy(doc.id, async () => {
      try {
        replace(await reindexDocument(doc.id))
      } catch (err) {
        toast.danger('Could not re-index', { description: errorDetail(err, 'Please try again.') })
      }
    })

  const handleDelete = (doc: KnowledgeDocument) =>
    withBusy(doc.id, async () => {
      try {
        await deleteDocument(doc.id)
        setDocuments((docs) => (docs ?? []).filter((d) => d.id !== doc.id))
        toast.success('Deleted', { description: doc.filename })
      } catch (err) {
        toast.danger('Could not delete', { description: errorDetail(err, 'Please try again.') })
      }
    })

  return (
    <Page
      title="Knowledge Base"
      description="Documents and pages you add are digested so chat can search them."
      width="max-w-2xl"
    >
      <div className="flex flex-col gap-6">
        <Documents onAdded={(doc) => setDocuments((docs) => [doc, ...(docs ?? [])])} />
        <DocumentList
          documents={documents}
          busyIds={busyIds}
          onReindex={handleReindex}
          onDelete={handleDelete}
        />
      </div>
    </Page>
  )
}

export default KnowledgeBasePage
