export interface TextBlock {
  type: 'text'
  text: string
}

export interface ThinkingBlock {
  type: 'thinking'
  thinking: string
}

export interface ImageBlock {
  type: 'image'
  url: string
  alt?: string
}

export interface CitationBlock {
  type: 'citation'
  document_id: string
  chunk_text: string
  source_name: string
}

export interface ToolCallBlock {
  type: 'tool_call'
  name: string
  input: Record<string, unknown>
}

export interface ToolResultBlock {
  type: 'tool_result'
  name: string
  output: string
}

export type ContentBlock =
  | TextBlock
  | ThinkingBlock
  | ImageBlock
  | CitationBlock
  | ToolCallBlock
  | ToolResultBlock

export interface Message {
  id?: string
  sender: 'USER' | 'ASSISTANT'
  text: string
  content: ContentBlock[]
  timestamp: string
}

export interface ContentDelta {
  type: string
  delta: string
  url?: string
  alt?: string
  document_id?: string
  chunk_text?: string
  source_name?: string
  name?: string
  input?: Record<string, unknown>
  output?: string
}
