import api from './api'

export type DocumentStatus = 'UPLOADED' | 'DIGESTING' | 'READY' | 'ERROR'

export interface KnowledgeDocument {
  id: string
  filename: string
  source_type: 'FILE' | 'URL'
  source_url: string | null
  mime_type: string | null
  size_bytes: number | null
  status: DocumentStatus
  error_message: string | null
  chunk_count: number
  created_at: string
  reindexable: boolean
}

export const ACCEPTED_FILE_TYPES = '.txt,.md,.markdown,.pdf,.html,.htm'

export function isPending(doc: KnowledgeDocument): boolean {
  return doc.status === 'UPLOADED' || doc.status === 'DIGESTING'
}

export async function listDocuments(): Promise<KnowledgeDocument[]> {
  const { data } = await api.get('/documents')
  return data
}

export async function uploadDocument(file: File): Promise<KnowledgeDocument> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await api.post('/documents/upload', formData)
  return data
}

export async function addUrl(url: string): Promise<KnowledgeDocument> {
  const { data } = await api.post('/documents/url', { url })
  return data
}

export async function reindexDocument(id: string): Promise<KnowledgeDocument> {
  const { data } = await api.post(`/documents/${id}/reindex`)
  return data
}

export async function deleteDocument(id: string): Promise<void> {
  await api.delete(`/documents/${id}`)
}

/** The API's `detail` message when there is one, else a fallback. */
export function errorDetail(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
  return typeof detail === 'string' ? detail : fallback
}
