export type ExtensionMode = 'with_backend' | 'non_backend'

export interface ExtensionSettings {
  mode: ExtensionMode
  backendUrl: string
  openaiApiKey: string
  openaiModel: string
}

export interface Message {
  id: string
  sender: 'USER' | 'ASSISTANT'
  text: string
  timestamp: string
}

export interface Task {
  id: string
  title: string
  description?: string
  status: 'TODO' | 'WORKING' | 'DONE'
  due_date?: string
  created_at: string
}

export interface SelectedTextInfo {
  text: string
  url: string
  title: string
}

export const DEFAULT_SETTINGS: ExtensionSettings = {
  mode: 'with_backend',
  backendUrl: 'http://localhost:8000',
  openaiApiKey: '',
  openaiModel: 'gpt-4o-mini',
}
