import React from 'react'
import { Badge } from '@/components/ui/badge'
import type { ExtensionMode } from '@/types'

interface ModeBadgeProps {
  mode: ExtensionMode
}

const ModeBadge: React.FC<ModeBadgeProps> = ({ mode }) => {
  return (
    <Badge variant={mode === 'with_backend' ? 'default' : 'secondary'} className="text-[10px]">
      {mode === 'with_backend' ? 'Backend' : 'Direct'}
    </Badge>
  )
}

export default ModeBadge
