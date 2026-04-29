import React from 'react'

interface ThinkingAnimationProps {
  size?: 'sm' | 'md'
  text?: string
}

/**
 * Gemini-style sparkle shimmer animation indicating the AI is thinking.
 */
const ThinkingAnimation: React.FC<ThinkingAnimationProps> = ({
  size = 'md',
  text = 'Thinking',
}) => {
  const dotSize = size === 'sm' ? 'w-1.5 h-1.5' : 'w-2 h-2'
  const containerClass =
    size === 'sm' ? 'gap-1.5 py-1' : 'gap-2 py-1.5'

  return (
    <div
      className={`inline-flex items-center ${containerClass} select-none`}
      aria-label="AI is thinking"
    >
      <span className="text-xs text-muted-foreground font-medium mr-1">
        {text}
      </span>
      <div className="flex items-center gap-1">
        <span
          className={`${dotSize} rounded-full bg-primary/70 thinking-dot`}
          style={{ animationDelay: '0ms' }}
        />
        <span
          className={`${dotSize} rounded-full bg-primary/70 thinking-dot`}
          style={{ animationDelay: '200ms' }}
        />
        <span
          className={`${dotSize} rounded-full bg-primary/70 thinking-dot`}
          style={{ animationDelay: '400ms' }}
        />
      </div>
      {/* Shimmer sweep overlay */}
      <div className="relative overflow-hidden ml-1 w-8 h-4">
        <div className="thinking-shimmer absolute inset-0" />
      </div>
    </div>
  )
}

export default ThinkingAnimation
