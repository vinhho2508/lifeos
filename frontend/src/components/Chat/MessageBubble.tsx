import React from 'react'
import { ContentBlock, Message, ToolResultBlock } from '@/types/chat'
import TextBlock from './ContentBlocks/TextBlock'
import ThinkingBlock from './ContentBlocks/ThinkingBlock'
import ImageBlock from './ContentBlocks/ImageBlock'
import ToolStepBlock from './ContentBlocks/ToolStepBlock'
import ThinkingAnimation from './ThinkingAnimation'

interface MessageBubbleProps {
  message: Message
  isStreaming?: boolean
  isLast?: boolean
}

interface ContentBlockRendererProps {
  block: ContentBlock
  isStreaming?: boolean
  results: Map<string, ToolResultBlock>
}

const ContentBlockRenderer: React.FC<ContentBlockRendererProps> = ({
  block,
  isStreaming,
  results,
}) => {
  switch (block.type) {
    case 'text':
      return <TextBlock text={block.text} />
    case 'thinking':
      return <ThinkingBlock thinking={block.thinking} isStreaming={isStreaming} />
    case 'image':
      return <ImageBlock url={block.url} alt={block.alt} />
    case 'citation':
      return (
        <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 text-primary px-2.5 py-1 text-xs font-medium my-1">
          <span>Source: {block.source_name}</span>
        </div>
      )
    case 'tool_call':
      return <ToolStepBlock call={block} result={results.get(block.id)} />
    case 'tool_result':
      // Rendered inside the card of its tool_call.
      return null
    case 'error':
      return (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive my-1">
          {block.message}
        </div>
      )
    default:
      return null
  }
}

const MessageBubble: React.FC<MessageBubbleProps> = ({
  message,
  isStreaming = false,
  isLast = false,
}) => {
  const isUser = message.sender === 'USER'

  // Show thinking animation inside the assistant bubble when:
  // - it's the last message
  // - we're streaming
  // - the bubble has zero content blocks
  const showBubbleAnimation = !isUser && isLast && isStreaming && message.content.length === 0

  // Tool results render inside the card of the tool_call with the same id.
  const results = new Map<string, ToolResultBlock>()
  for (const block of message.content ?? []) {
    if (block.type === 'tool_result') results.set(block.id, block)
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser ? 'bg-primary text-primary-foreground' : 'bg-muted text-foreground'
        }`}
      >
        {message.content && message.content.length > 0 ? (
          message.content.map((block, idx) => (
            <ContentBlockRenderer
              key={idx}
              block={block}
              isStreaming={isStreaming}
              results={results}
            />
          ))
        ) : showBubbleAnimation ? (
          <ThinkingAnimation size="sm" />
        ) : (
          <span className="text-sm whitespace-pre-wrap">{message.text}</span>
        )}
      </div>
    </div>
  )
}

export default MessageBubble
