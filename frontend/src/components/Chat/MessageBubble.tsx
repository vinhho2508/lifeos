import React from 'react'
import { ContentBlock, Message } from '@/types/chat'
import TextBlock from './ContentBlocks/TextBlock'
import ThinkingBlock from './ContentBlocks/ThinkingBlock'
import ImageBlock from './ContentBlocks/ImageBlock'

interface MessageBubbleProps {
  message: Message
}

const ContentBlockRenderer: React.FC<{ block: ContentBlock }> = ({ block }) => {
  switch (block.type) {
    case 'text':
      return <TextBlock text={block.text} />
    case 'thinking':
      return <ThinkingBlock thinking={block.thinking} />
    case 'image':
      return <ImageBlock url={block.url} alt={block.alt} />
    case 'citation':
      return (
        <div className="inline-flex items-center gap-1.5 rounded-full bg-primary/10 text-primary px-2.5 py-1 text-xs font-medium my-1">
          <span>Source: {block.source_name}</span>
        </div>
      )
    case 'tool_call':
      return (
        <div className="flex items-center gap-2 rounded-md bg-muted/60 px-3 py-2 text-xs text-muted-foreground my-1">
          <span className="font-medium">Tool:</span>
          <span>{block.name}</span>
        </div>
      )
    case 'tool_result':
      return (
        <div className="rounded-md bg-muted/40 px-3 py-2 text-xs text-muted-foreground my-1">
          <span className="font-medium">Result:</span> {block.output}
        </div>
      )
    default:
      return null
  }
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ message }) => {
  const isUser = message.sender === 'USER'

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-foreground'
        }`}
      >
        {message.content && message.content.length > 0 ? (
          message.content.map((block, idx) => (
            <ContentBlockRenderer key={idx} block={block} />
          ))
        ) : (
          <span className="text-sm whitespace-pre-wrap">{message.text}</span>
        )}
      </div>
    </div>
  )
}

export default MessageBubble
