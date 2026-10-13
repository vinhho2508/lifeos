import React from 'react'
import { BrainCircuit } from 'lucide-react'
import ThinkingAnimation from '../ThinkingAnimation'
import StepCard from './StepCard'

interface ThinkingBlockProps {
  thinking: string
  isStreaming?: boolean
}

const ThinkingBlock: React.FC<ThinkingBlockProps> = ({ thinking, isStreaming = false }) => {
  const isEmpty = !thinking || thinking.trim().length === 0

  // Show animation inside the thinking block when empty and streaming
  const showAnimation = isEmpty && isStreaming

  return (
    <StepCard icon={<BrainCircuit className="size-3.5" />} title="Thinking">
      {showAnimation ? (
        <ThinkingAnimation size="sm" />
      ) : (
        <pre className="whitespace-pre-wrap font-mono text-xs leading-relaxed text-muted">
          {thinking}
        </pre>
      )}
    </StepCard>
  )
}

export default ThinkingBlock
