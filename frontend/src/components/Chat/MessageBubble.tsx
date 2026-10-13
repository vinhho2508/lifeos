import React from 'react'
import { Alert, Chip } from '@heroui/react'
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
        <Chip size="sm" color="accent" variant="soft" className="my-1">
          Source: {block.source_name}
          {block.page != null && ` · p.${block.page}`}
          {block.heading_path && ` · ${block.heading_path}`}
        </Chip>
      )
    case 'tool_call':
      return <ToolStepBlock call={block} result={results.get(block.id)} />
    case 'tool_result':
      // Rendered inside the card of its tool_call.
      return null
    case 'error':
      return (
        <Alert status="danger" className="my-1">
          <Alert.Content>
            <Alert.Description>{block.message}</Alert.Description>
          </Alert.Content>
        </Alert>
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
        className={
          isUser
            ? 'max-w-[85%] rounded-2xl rounded-br-md bg-accent px-4 py-2.5 text-sm text-accent-foreground'
            : 'w-full min-w-0 text-sm leading-relaxed text-foreground'
        }
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
          <span className="whitespace-pre-wrap">{message.text}</span>
        )}
      </div>
    </div>
  )
}

export default MessageBubble
