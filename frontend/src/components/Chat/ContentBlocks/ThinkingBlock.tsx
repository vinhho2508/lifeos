import React, { useState } from 'react'
import { ChevronDown, ChevronRight, BrainCircuit } from 'lucide-react'
import ThinkingAnimation from '../ThinkingAnimation'

interface ThinkingBlockProps {
  thinking: string
  isStreaming?: boolean
}

const ThinkingBlock: React.FC<ThinkingBlockProps> = ({
  thinking,
  isStreaming = false,
}) => {
  const [expanded, setExpanded] = useState(false)
  const isEmpty = !thinking || thinking.trim().length === 0

  // Show animation inside the thinking block when empty and streaming
  const showAnimation = isEmpty && isStreaming

  return (
    <div className="my-2 rounded-lg border border-muted bg-muted/40 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 w-full px-3 py-2 text-left text-xs font-medium text-muted-foreground hover:bg-muted/60 transition-colors"
      >
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5" />
        )}
        <BrainCircuit className="w-3.5 h-3.5" />
        <span>Thinking</span>
      </button>
      {expanded && (
        <div className="px-3 pb-3">
          {showAnimation ? (
            <ThinkingAnimation size="sm" />
          ) : (
            <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
              {thinking}
            </pre>
          )}
        </div>
      )}
    </div>
  )
}

export default ThinkingBlock
