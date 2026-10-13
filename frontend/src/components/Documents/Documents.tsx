import React, { useRef, useState } from 'react'
import { FileUp } from 'lucide-react'
import { Button, Card, toast } from '@heroui/react'
import api from '../../services/api'

const Documents: React.FC = () => {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      await api.post('/documents/upload', formData)
      toast.success('Document uploaded and digested')
      setFile(null)
      if (inputRef.current) inputRef.current.value = ''
    } catch (err) {
      console.error('Upload error:', err)
      toast.danger('Upload failed', { description: 'The document could not be digested.' })
    } finally {
      setUploading(false)
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
            : 'It will be split and indexed for search.'}
        </span>
        <input
          ref={inputRef}
          type="file"
          className="sr-only"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
      </label>
      <Button fullWidth isDisabled={!file} isPending={uploading} onPress={handleUpload}>
        {uploading ? 'Digesting…' : 'Upload & digest'}
      </Button>
    </Card>
  )
}

export default Documents
