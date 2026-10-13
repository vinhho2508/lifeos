import React from 'react'
import { FileText, Globe, RefreshCw, Trash2 } from 'lucide-react'
import { Button, Card, Chip, Skeleton } from '@heroui/react'
import { DocumentStatus, KnowledgeDocument, isPending } from '@/services/documentsApi'

const statusMeta: Record<
  DocumentStatus,
  { label: string; color: 'default' | 'warning' | 'success' | 'danger' }
> = {
  UPLOADED: { label: 'Queued', color: 'default' },
  DIGESTING: { label: 'Digesting', color: 'warning' },
  READY: { label: 'Ready', color: 'success' },
  ERROR: { label: 'Failed', color: 'danger' },
}

function hostname(url: string): string {
  try {
    return new URL(url).hostname
  } catch {
    return url
  }
}

function details(doc: KnowledgeDocument): string {
  const parts: string[] = []
  if (doc.source_type === 'URL' && doc.source_url) parts.push(hostname(doc.source_url))
  if (doc.size_bytes) parts.push(`${(doc.size_bytes / 1024).toFixed(1)} KB`)
  if (doc.status === 'READY') parts.push(`${doc.chunk_count} passages`)
  parts.push(new Date(doc.created_at).toLocaleDateString())
  return parts.join(' · ')
}

interface DocumentListProps {
  documents: KnowledgeDocument[] | null
  busyIds: Set<string>
  onReindex: (doc: KnowledgeDocument) => void
  onDelete: (doc: KnowledgeDocument) => void
}

const DocumentList: React.FC<DocumentListProps> = ({ documents, busyIds, onReindex, onDelete }) => {
  if (documents === null) {
    return (
      <Card className="gap-3">
        {[0, 1, 2].map((i) => (
          <Skeleton key={i} className="h-10 rounded-lg" />
        ))}
      </Card>
    )
  }
  if (documents.length === 0) {
    return (
      <Card className="items-center py-8 text-center text-sm text-muted">
        No documents yet. Upload one so chat can search it.
      </Card>
    )
  }

  return (
    <Card className="gap-0 p-0">
      <ul className="divide-y divide-border">
        {documents.map((doc) => {
          const meta = statusMeta[doc.status]
          const Icon = doc.source_type === 'URL' ? Globe : FileText
          const busy = busyIds.has(doc.id)
          return (
            <li key={doc.id} className="flex items-start gap-3 px-4 py-3">
              <Icon className="mt-0.5 size-4 shrink-0 text-muted" aria-hidden />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="truncate text-sm font-medium" title={doc.filename}>
                    {doc.filename}
                  </span>
                  <Chip size="sm" variant="soft" color={meta.color}>
                    {meta.label}
                  </Chip>
                </div>
                <p className="text-xs text-muted">{details(doc)}</p>
                {doc.status === 'ERROR' && doc.error_message && (
                  <p className="mt-1 text-xs text-danger">{doc.error_message}</p>
                )}
              </div>
              <div className="flex shrink-0 gap-1">
                {doc.reindexable && (
                  <Button
                    isIconOnly
                    size="sm"
                    variant="ghost"
                    aria-label={doc.status === 'ERROR' ? 'Retry' : 'Re-index'}
                    isDisabled={isPending(doc) || busy}
                    onPress={() => onReindex(doc)}
                  >
                    <RefreshCw className="size-4" aria-hidden />
                  </Button>
                )}
                <Button
                  isIconOnly
                  size="sm"
                  variant="ghost"
                  aria-label="Delete"
                  isDisabled={busy}
                  onPress={() => onDelete(doc)}
                >
                  <Trash2 className="size-4" aria-hidden />
                </Button>
              </div>
            </li>
          )
        })}
      </ul>
    </Card>
  )
}

export default DocumentList
