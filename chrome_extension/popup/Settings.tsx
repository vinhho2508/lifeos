import React, { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Settings2, Save, Check } from 'lucide-react'
import { getSettings, setSettings } from '@/lib/storage'
import type { ExtensionSettings } from '@/types'

const SettingsPage: React.FC = () => {
  const [settings, setLocalSettings] = useState<ExtensionSettings | null>(null)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    getSettings().then(setLocalSettings)
  }, [])

  const handleSave = async () => {
    if (!settings) return
    await setSettings(settings)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const updateField = <K extends keyof ExtensionSettings>(
    key: K,
    value: ExtensionSettings[K]
  ) => {
    setLocalSettings((prev) => (prev ? { ...prev, [key]: value } : prev))
  }

  if (!settings) {
    return (
      <div className="flex h-[320px] items-center justify-center">
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    )
  }

  return (
    <div className="p-4">
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center gap-2">
            <Settings2 className="h-5 w-5" />
            <CardTitle className="text-base">LifeOS Settings</CardTitle>
          </div>
          <CardDescription>Configure your extension mode and API keys</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Mode Selection */}
          <div>
            <label className="mb-1.5 block text-sm font-medium">Mode</label>
            <div className="flex gap-2">
              <button
                onClick={() => updateField('mode', 'with_backend')}
                className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                  settings.mode === 'with_backend'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-input bg-background hover:bg-accent'
                }`}
              >
                With Backend
              </button>
              <button
                onClick={() => updateField('mode', 'non_backend')}
                className={`flex-1 rounded-md border px-3 py-2 text-sm transition-colors ${
                  settings.mode === 'non_backend'
                    ? 'border-primary bg-primary/10 text-primary'
                    : 'border-input bg-background hover:bg-accent'
                }`}
              >
                Direct (OpenAI)
              </button>
            </div>
          </div>

          {/* Backend Settings */}
          {settings.mode === 'with_backend' && (
            <div>
              <label className="mb-1.5 block text-sm font-medium">Backend URL</label>
              <Input
                value={settings.backendUrl}
                onChange={(e) => updateField('backendUrl', e.target.value)}
                placeholder="http://localhost:8000"
              />
              <p className="mt-1 text-xs text-muted-foreground">
                Must be logged into the LifeOS web app.
              </p>
            </div>
          )}

          {/* Direct Settings */}
          {settings.mode === 'non_backend' && (
            <>
              <div>
                <label className="mb-1.5 block text-sm font-medium">OpenAI API Key</label>
                <Input
                  type="password"
                  value={settings.openaiApiKey}
                  onChange={(e) => updateField('openaiApiKey', e.target.value)}
                  placeholder="sk-..."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-sm font-medium">Model</label>
                <Input
                  value={settings.openaiModel}
                  onChange={(e) => updateField('openaiModel', e.target.value)}
                  placeholder="gpt-4o-mini"
                />
              </div>
            </>
          )}

          {/* Save Button */}
          <Button onClick={handleSave} className="w-full">
            {saved ? (
              <>
                <Check className="mr-2 h-4 w-4" />
                Saved
              </>
            ) : (
              <>
                <Save className="mr-2 h-4 w-4" />
                Save Settings
              </>
            )}
          </Button>

          {saved && (
            <Badge variant="outline" className="w-full justify-center">
              Settings saved successfully
            </Badge>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

export default SettingsPage
