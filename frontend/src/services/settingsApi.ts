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
    timezone: string
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
  timezone?: string
}): Promise<SettingsData> {
  const { data } = await api.put('/settings', body)
  return data
}


export function browserTimezone(): string {
  return Intl.DateTimeFormat().resolvedOptions().timeZone
}

const TZ_SYNCED_KEY = 'timezoneSynced'

/**
 * Relative dates in chat ("Friday 9am") resolve in the saved timezone, which defaults to
 * UTC. Once per browser, replace that default with the browser's zone.
 */
export async function syncBrowserTimezone(): Promise<void> {
  if (localStorage.getItem(TZ_SYNCED_KEY)) return
  const data = await fetchSettings()
  const tz = browserTimezone()
  if (data.settings.timezone === 'UTC' && tz && tz !== 'UTC') {
    await updateSettings({ timezone: tz })
  }
  localStorage.setItem(TZ_SYNCED_KEY, '1')
}
