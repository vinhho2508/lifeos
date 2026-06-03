import React, { useEffect, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Save, Check } from 'lucide-react'
import { fetchSettings, updateSettings, ProviderInfo } from '../services/settingsApi'

const SettingsPage: React.FC = () => {
  const [providers, setProviders] = useState<Record<string, ProviderInfo>>({})
  const [selectedProvider, setSelectedProvider] = useState('')
  const [selectedModel, setSelectedModel] = useState('')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      const data = await fetchSettings()
      setProviders(data.available_providers)
      setSelectedProvider(data.settings.chat_provider)
      setSelectedModel(data.settings.chat_model)
    } catch {
      // API not ready yet
    }
  }

  async function handleSave() {
    setSaving(true)
    setSaved(false)
    try {
      await updateSettings({
        chat_provider: selectedProvider,
        chat_model: selectedModel,
      })
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
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

  return (
    <div className="mx-auto max-w-2xl">
      <Card>
        <CardHeader>
          <CardTitle>Settings</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="provider">AI Provider</Label>
            <select
              id="provider"
              value={selectedProvider}
              onChange={(e) => handleProviderChange(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {Object.entries(providers).map(([key, info]) => (
                <option key={key} value={key}>
                  {info.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <Label htmlFor="model">Model</Label>
            <select
              id="model"
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          <Button onClick={handleSave} disabled={saving}>
            {saved ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                {saving ? 'Saving...' : 'Save'}
              </>
            )}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage
