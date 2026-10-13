import React, { useState, useEffect } from 'react'
import { Button, Card, Description, Input, Label, TextField, Toast, toast } from '@heroui/react'
import { Save, Settings2 } from 'lucide-react'
import { getSettings, setSettings } from '@/lib/storage'
import type { ExtensionSettings } from '@/types'

const SettingsPage: React.FC = () => {
  const [settings, setLocalSettings] = useState<ExtensionSettings | null>(null)

  useEffect(() => {
    getSettings().then(setLocalSettings)
  }, [])

  const handleSave = async () => {
    if (!settings) return
    await setSettings(settings)
    toast.success('Settings saved')
  }

  const updateField = <K extends keyof ExtensionSettings>(key: K, value: ExtensionSettings[K]) => {
    setLocalSettings((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  if (!settings) {
    return (
      <div className="flex h-[320px] items-center justify-center">
        <p className="text-sm text-muted">Loading…</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      <Toast.Provider />
      <Card className="gap-4">
        <Card.Header>
          <div className="flex items-center gap-2">
            <Settings2 className="size-4 text-muted" />
            <Card.Title className="text-base">LifeOS settings</Card.Title>
          </div>
          <Card.Description>Configure your extension mode and API keys.</Card.Description>
        </Card.Header>
        <Card.Content className="space-y-4">
          <div role="group" aria-label="Mode" className="space-y-1.5">
            <span className="text-sm font-medium">Mode</span>
            <div className="grid grid-cols-2 gap-2">
              <Button
                size="sm"
                variant={settings.mode === 'with_backend' ? 'primary' : 'secondary'}
                aria-pressed={settings.mode === 'with_backend'}
                onPress={() => updateField('mode', 'with_backend')}
              >
                With backend
              </Button>
              <Button
                size="sm"
                variant={settings.mode === 'non_backend' ? 'primary' : 'secondary'}
                aria-pressed={settings.mode === 'non_backend'}
                onPress={() => updateField('mode', 'non_backend')}
              >
                Direct (OpenAI)
              </Button>
            </div>
          </div>

          {settings.mode === 'with_backend' && (
            <TextField
              fullWidth
              value={settings.backendUrl}
              onChange={(v) => updateField('backendUrl', v)}
            >
              <Label>Backend URL</Label>
              <Input placeholder="http://localhost:8000" />
              <Description>Must be logged into the LifeOS web app.</Description>
            </TextField>
          )}

          {settings.mode === 'non_backend' && (
            <>
              <p className="text-xs text-muted">
                Plain chat only: the agent&apos;s tools (tasks, documents, images) need the backend.
              </p>
              <TextField
                fullWidth
                type="password"
                value={settings.openaiApiKey}
                onChange={(v) => updateField('openaiApiKey', v)}
              >
                <Label>OpenAI API key</Label>
                <Input placeholder="sk-..." />
              </TextField>
              <TextField
                fullWidth
                value={settings.openaiModel}
                onChange={(v) => updateField('openaiModel', v)}
              >
                <Label>Model</Label>
                <Input placeholder="gpt-5.4-nano" />
              </TextField>
            </>
          )}

          <Button fullWidth onPress={handleSave}>
            <Save className="size-4" />
            Save settings
          </Button>
        </Card.Content>
      </Card>
    </div>
  )
}

export default SettingsPage
