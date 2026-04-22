import React, { useState } from 'react'
import api from '../../services/api'

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
    <div className="documents-container">
      <h2>Knowledge Base</h2>
      <input type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? 'Digesting...' : 'Upload & Digest'}
      </button>
    </div>
  )
}

export default Documents
