import React, { useRef, useState } from 'react'
import { FileUp, Link2 } from 'lucide-react'
import { Button, Card, Input, toast } from '@heroui/react'
import {
  ACCEPTED_FILE_TYPES,
  KnowledgeDocument,
  addUrl,
  errorDetail,
  uploadDocument,
} from '@/services/documentsApi'

interface DocumentsProps {
  onAdded: (doc: KnowledgeDocument) => void
}

/** Add to the knowledge base: upload a file or submit a web page URL. */
const Documents: React.FC<DocumentsProps> = ({ onAdded }) => {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [url, setUrl] = useState('')
  const [adding, setAdding] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    try {
      onAdded(await uploadDocument(file))
      toast.success('Uploaded', { description: `${file.name} is being digested.` })
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (err) {
      toast.danger('Upload failed', { description: errorDetail(err, 'Please try again.') })
    } finally {
      setUploading(false)
    }
  }

  const handleAddUrl = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!url.trim()) return
    setAdding(true)
    try {
      onAdded(await addUrl(url.trim()))
      toast.success('Page added', { description: 'It is being fetched and digested.' })
      setUrl('')
    } catch (err) {
      toast.danger('Could not add page', { description: errorDetail(err, 'Check the URL.') })
    } finally {
      setAdding(false)
    }
  }

  return (
    <Card className="gap-4">
      <label className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border border-dashed border-border px-6 py-10 text-center transition-colors hover:bg-surface-secondary focus-within:ring-2 focus-within:ring-focus">
        <FileUp className="size-6 text-muted" aria-hidden />
        <span className="text-sm font-medium">
          {file ? file.name : 'Choose a document to upload'}
        </span>
        <span className="text-xs text-muted">
          {file
            ? `${(file.size / 1024).toFixed(1)} KB`
            : 'Text, Markdown, PDF or HTML, up to 20 MB.'}
        </span>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_FILE_TYPES}
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </label>
      <Button fullWidth isDisabled={!file} isPending={uploading} onPress={handleUpload}>
        {uploading ? 'Uploading…' : 'Upload'}
      </Button>

      <form className="flex gap-2" onSubmit={handleAddUrl}>
        <div className="relative flex-1">
          <Link2
            className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted"
            aria-hidden
          />
          <Input
            aria-label="Web page URL"
            type="url"
            placeholder="https://example.com/article"
            fullWidth
            className="pl-9"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />
        </div>
        <Button type="submit" variant="secondary" isDisabled={!url.trim()} isPending={adding}>
          Add page
        </Button>
      </form>
    </Card>
  )
}

export default Documents
