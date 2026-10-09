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
  id: string
  name: string
  input: Record<string, unknown>
}

export interface ToolResultBlock {
  type: 'tool_result'
  id: string
  name: string
  status: 'ok' | 'error'
  summary: string
  output: unknown
}

export interface ErrorBlock {
  type: 'error'
  message: string
}

export type ContentBlock =
  | TextBlock
  | ThinkingBlock
  | ImageBlock
  | CitationBlock
  | ToolCallBlock
  | ToolResultBlock
  | ErrorBlock

export interface Message {
  id?: string
  sender: 'USER' | 'ASSISTANT'
  text: string
  content: ContentBlock[]
  timestamp: string
}

/** One NDJSON line from POST /chat/stream (specs/002-agent-loop/contracts/chat-stream.md). */
export interface ContentDelta {
  type: string
  delta?: string
  id?: string
  url?: string
  alt?: string
  document_id?: string
  chunk_text?: string
  source_name?: string
  name?: string
  input?: Record<string, unknown>
  status?: 'ok' | 'error'
  summary?: string
  output?: unknown
  message?: string
  stop_reason?: 'end_turn' | 'max_steps' | 'error'
}
