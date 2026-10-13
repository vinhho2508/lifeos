import React, { useEffect, useState } from 'react'
import { Button, Card, toast } from '@heroui/react'
import { Save } from 'lucide-react'
import SelectField from '@/components/forms/SelectField'
import Page from '@/components/Layout/Page'
import {
  browserTimezone,
  fetchSettings,
  updateSettings,
  ProviderInfo,
} from '../services/settingsApi'

// Intl.supportedValuesOf is ES2022; tsconfig targets the ES2020 lib.
const TIMEZONES: string[] =
  (Intl as { supportedValuesOf?: (key: string) => string[] }).supportedValuesOf?.('timeZone') ?? []

const SettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [timezone, setTimezone] = useState(browserTimezone())
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      const data = await fetchSettings()
      setProviders(data.available_providers)
      setSelectedProvider(data.settings.chat_provider)
      setSelectedModel(data.settings.chat_model)
      setTimezone(data.settings.timezone)
    } catch {
      // API not ready yet
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      await updateSettings({
        chat_provider: selectedProvider,
        chat_model: selectedModel,
        timezone,
      })
      toast.success('Settings saved')
    } catch {
      toast.danger('Could not save settings')
    } finally {
      setSaving(false)
    }
  }

  function handleProviderChange(provider: string) {
    setSelectedProvider(provider)
    const providerInfo = providers[provider]
    if (providerInfo) {
      setSelectedModel(providerInfo.default_model || providerInfo.models[0])
    }
  }

  const models = providers[selectedProvider]?.models || []

  const timezones = TIMEZONES.includes(timezone) ? TIMEZONES : [timezone, ...TIMEZONES]
  const asOptions = (values: string[]) => values.map((v) => ({ value: v, label: v }))

  return (
    <Page title="Settings" description="Choose the AI model and your timezone." width="max-w-xl">
      <Card className="gap-6">
        <SelectField
          label="AI provider"
          value={selectedProvider}
          options={Object.entries(providers).map(([key, info]) => ({
            value: key,
            label: info.name,
          }))}
          onChange={handleProviderChange}
        />
        <SelectField
          label="Model"
          value={selectedModel}
          options={asOptions(models)}
          onChange={setSelectedModel}
        />
        <SelectField
          label="Timezone"
          value={timezone}
          options={asOptions(timezones)}
          onChange={setTimezone}
          description="Used to schedule tasks from chat, like “Friday 9am”."
        />
        <div>
          <Button isPending={saving} onPress={handleSave}>
            <Save className="size-4" />
            {saving ? 'Saving…' : 'Save changes'}
          </Button>
        </div>
      </Card>
    </Page>
  )
}

export default SettingsPage
