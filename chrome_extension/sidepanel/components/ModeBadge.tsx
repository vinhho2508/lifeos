import React from 'react'
import { Chip } from '@heroui/react'
import type { ExtensionMode } from '@/types'

interface ModeBadgeProps {
  mode: ExtensionMode
}

const ModeBadge: React.FC<ModeBadgeProps> = ({ mode }) => {
  return (
    <Chip size="sm" color={mode === 'with_backend' ? 'accent' : 'default'} variant="soft">
      {mode === 'with_backend' ? 'Backend' : 'Direct'}
    </Chip>
  )
}

export default ModeBadge
