import React, { useState } from 'react'
import api from '../../services/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

const Documents: React.FC = () => {
  const [file, setFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      await api.post('/documents/upload', formData)
      alert('Document uploaded and digested!')
    } catch (err) {
      console.error('Upload error:', err)
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="flex flex-col gap-4">
      <Input
        type="file"
        onChange={(e) => setFile(e.target.files?.[0] || null)}
      />
      <Button onClick={handleUpload} disabled={uploading}>
        {uploading ? 'Digesting...' : 'Upload & Digest'}
      </Button>
    </div>
  )
}

export default Documents
