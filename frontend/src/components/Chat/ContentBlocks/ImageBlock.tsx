import React, { useState } from 'react'
import { ImageIcon } from 'lucide-react'

interface ImageBlockProps {
  url: string
  alt?: string
}

const ImageBlock: React.FC<ImageBlockProps> = ({ url, alt }) => {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)

  if (error) {
    return (
      <div className="my-2 rounded-lg border border-destructive/30 bg-destructive/10 p-4 flex items-center gap-2 text-sm text-destructive">
        <ImageIcon className="w-4 h-4" />
        <span>Failed to load image</span>
      </div>
    )
  }

  return (
    <div className="my-2">
      {!loaded && (
        <div className="rounded-lg bg-muted animate-pulse h-48 w-full flex items-center justify-center">
          <ImageIcon className="w-8 h-8 text-muted-foreground/50" />
        </div>
      )}
      <img
        src={url}
        alt={alt || 'Generated image'}
        className={`rounded-lg max-w-full h-auto transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
      {alt && loaded && (
        <p className="text-xs text-muted-foreground mt-1">{alt}</p>
      )}
    </div>
  )
}

export default ImageBlock
