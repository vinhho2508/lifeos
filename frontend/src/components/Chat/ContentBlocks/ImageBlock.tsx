import React, { useState } from 'react'
import { ImageIcon } from 'lucide-react'
import { Skeleton } from '@heroui/react'

interface ImageBlockProps {
  url: string
  alt?: string
}

const ImageBlock: React.FC<ImageBlockProps> = ({ url, alt }) => {
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState(false)

  if (error) {
    return (
      <div className="my-2 flex items-center gap-2 rounded-lg border border-danger/30 bg-danger-soft p-4 text-sm text-danger-soft-foreground">
        <ImageIcon className="w-4 h-4" />
        <span>Failed to load image</span>
      </div>
    )
  }

  return (
    <div className="my-2">
      {!loaded && (
        <Skeleton className="flex h-48 w-full items-center justify-center rounded-lg">
          <ImageIcon className="size-8 text-muted/50" />
        </Skeleton>
      )}
      <img
        src={url}
        alt={alt || 'Generated image'}
        className={`rounded-lg max-w-full h-auto transition-opacity duration-300 ${loaded ? 'opacity-100' : 'opacity-0'}`}
        onLoad={() => setLoaded(true)}
        onError={() => setError(true)}
      />
      {alt && loaded && <p className="mt-1 text-xs text-muted">{alt}</p>}
    </div>
  )
}

export default ImageBlock
