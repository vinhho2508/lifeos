import api from './api'

export interface ProviderInfo {
  name: string
  models: string[]
  default_model: string
}

export interface SettingsData {
  settings: {
    chat_provider: string
    chat_model: string
  }
  available_providers: Record<string, ProviderInfo>
}

export async function fetchSettings(): Promise<SettingsData> {
  const { data } = await api.get('/settings')
  return data
}

export async function updateSettings(body: {
  chat_provider?: string
  chat_model?: string
}): Promise<SettingsData> {
  const { data } = await api.put('/settings', body)
  return data
}
