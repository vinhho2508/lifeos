import React, { useState } from 'react'
import { ChevronDown, ChevronRight, BrainCircuit } from 'lucide-react'

interface ThinkingBlockProps {
  thinking: string
}

const ThinkingBlock: React.FC<ThinkingBlockProps> = ({ thinking }) => {
  const [expanded, setExpanded] = useState(false)

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
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono leading-relaxed">
            {thinking}
          </pre>
        </div>
      )}
    </div>
  )
}

export default ThinkingBlock
