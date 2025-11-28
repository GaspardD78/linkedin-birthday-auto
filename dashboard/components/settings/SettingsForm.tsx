"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Save, Loader2, AlertCircle } from "lucide-react"
import yaml from 'js-yaml'

interface ConfigData {
  bot_mode: string
  dry_run: boolean
  messaging_limits: {
    max_messages_per_run: number
    weekly_message_limit: number
    daily_message_limit: number
  }
  scheduling: {
    daily_start_hour: number
    daily_end_hour: number
    timezone: string
  }
  delays: {
    min_delay_seconds: number
    max_delay_seconds: number
    action_delay_min: number
    action_delay_max: number
  }
  birthday_filter: {
    process_today: boolean
    process_late: boolean
    max_days_late: number
  }
  messages: {
    messages_file: string
    late_messages_file: string
    avoid_repetition_years: number
  }
  debug: {
    log_level: string
    save_screenshots: boolean
    save_html: boolean
  }
}

export function SettingsForm() {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadConfig()
  }, [])

  const loadConfig = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/settings/yaml')
      if (!res.ok) throw new Error('Failed to load config')

      const data = await res.json()
      const parsed = yaml.load(data.content) as any

      setConfig({
        bot_mode: parsed.bot_mode || 'standard',
        dry_run: parsed.dry_run || false,
        messaging_limits: parsed.messaging_limits || {},
        scheduling: parsed.scheduling || {},
        delays: parsed.delays || {},
        birthday_filter: parsed.birthday_filter || {},
        messages: parsed.messages || {},
        debug: parsed.debug || {}
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!config) return

    setSaving(true)
    setError(null)
    setSuccess(false)

    try {
      // Fetch current YAML to preserve other fields
      const currentRes = await fetch('/api/settings/yaml')
      if (!currentRes.ok) throw new Error('Failed to fetch current config')

      const currentData = await currentRes.json()
      const currentConfig = yaml.load(currentData.content) as any

      // Merge updated values with current config
      const updatedConfig = {
        ...currentConfig,
        bot_mode: config.bot_mode,
        dry_run: config.dry_run,
        messaging_limits: config.messaging_limits,
        scheduling: config.scheduling,
        delays: config.delays,
        birthday_filter: config.birthday_filter,
        messages: config.messages,
        debug: config.debug
      }

      // Convert back to YAML
      const yamlContent = yaml.dump(updatedConfig, {
        indent: 2,
        lineWidth: 80,
        noRefs: true
      })

      const res = await fetch('/api/settings/yaml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: yamlContent })
      })

      if (!res.ok) throw new Error('Failed to save config')

      setSuccess(true)
      setTimeout(() => setSuccess(false), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config')
    } finally {
      setSaving(false)
    }
  }

  const updateConfig = (path: string[], value: any) => {
    if (!config) return

    const newConfig = { ...config }
    let current: any = newConfig

    for (let i = 0; i < path.length - 1; i++) {
      current = current[path[i]]
    }

    current[path[path.length - 1]] = value
    setConfig(newConfig)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-3 text-slate-400">Chargement de la configuration...</span>
      </div>
    )
  }

  if (!config) {
    return (
      <div className="text-center py-12 text-red-400">
        <AlertCircle className="h-12 w-12 mx-auto mb-3" />
        <p>{error || 'Impossible de charger la configuration'}</p>
        <Button onClick={loadConfig} className="mt-4">Réessayer</Button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="bg-red-900/20 border border-red-600 text-red-400 p-4 rounded-lg flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="bg-emerald-900/20 border border-emerald-600 text-emerald-400 p-4 rounded-lg">
          ✓ Configuration sauvegardée avec succès !
        </div>
      )}

      {/* Mode de fonctionnement */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Mode de fonctionnement</CardTitle>
          <CardDescription>Paramètres généraux du bot</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="bot_mode">Mode du bot</Label>
            <Select
              value={config.bot_mode}
              onValueChange={(val) => updateConfig(['bot_mode'], val)}
            >
              <SelectTrigger className="bg-slate-950 border-slate-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="standard">Standard (avec limites)</SelectItem>
                <SelectItem value="unlimited">Unlimited (sans limites)</SelectItem>
                <SelectItem value="custom">Custom</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Mode test (dry run)</Label>
              <p className="text-xs text-slate-400">Ne pas envoyer de vrais messages</p>
            </div>
            <Switch
              checked={config.dry_run}
              onCheckedChange={(val) => updateConfig(['dry_run'], val)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Limites d'envoi */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Limites d'envoi de messages</CardTitle>
          <CardDescription>Contrôlez le volume d'envoi pour éviter les restrictions LinkedIn</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="space-y-2">
              <Label htmlFor="max_per_run">Messages par exécution</Label>
              <Input
                id="max_per_run"
                type="number"
                min="1"
                max="100"
                value={config.messaging_limits.max_messages_per_run}
                onChange={(e) => updateConfig(['messaging_limits', 'max_messages_per_run'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="weekly_limit">Limite hebdomadaire</Label>
              <Input
                id="weekly_limit"
                type="number"
                min="1"
                max="500"
                value={config.messaging_limits.weekly_message_limit}
                onChange={(e) => updateConfig(['messaging_limits', 'weekly_message_limit'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="daily_limit">Limite quotidienne</Label>
              <Input
                id="daily_limit"
                type="number"
                min="1"
                max="100"
                value={config.messaging_limits.daily_message_limit}
                onChange={(e) => updateConfig(['messaging_limits', 'daily_message_limit'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Planification */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Planification</CardTitle>
          <CardDescription>Définissez les heures d'activité du bot</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="start_hour">Heure de début</Label>
              <Input
                id="start_hour"
                type="number"
                min="0"
                max="23"
                value={config.scheduling.daily_start_hour}
                onChange={(e) => updateConfig(['scheduling', 'daily_start_hour'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
              <p className="text-xs text-slate-400">0-23 (format 24h)</p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="end_hour">Heure de fin</Label>
              <Input
                id="end_hour"
                type="number"
                min="0"
                max="23"
                value={config.scheduling.daily_end_hour}
                onChange={(e) => updateConfig(['scheduling', 'daily_end_hour'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
              <p className="text-xs text-slate-400">0-23 (format 24h)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Délais entre actions */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Délais entre actions</CardTitle>
          <CardDescription>Temporisations pour paraître plus humain</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="min_delay">Délai minimum (secondes)</Label>
              <Input
                id="min_delay"
                type="number"
                min="30"
                max="600"
                value={config.delays.min_delay_seconds}
                onChange={(e) => updateConfig(['delays', 'min_delay_seconds'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="max_delay">Délai maximum (secondes)</Label>
              <Input
                id="max_delay"
                type="number"
                min="60"
                max="1200"
                value={config.delays.max_delay_seconds}
                onChange={(e) => updateConfig(['delays', 'max_delay_seconds'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Filtrage des anniversaires */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Gestion des anniversaires</CardTitle>
          <CardDescription>Configurez le traitement des anniversaires et des messages en retard</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Traiter les anniversaires du jour</Label>
              <p className="text-xs text-slate-400">Envoyer des messages pour les anniversaires d'aujourd'hui</p>
            </div>
            <Switch
              checked={config.birthday_filter.process_today}
              onCheckedChange={(val) => updateConfig(['birthday_filter', 'process_today'], val)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Traiter les anniversaires en retard</Label>
              <p className="text-xs text-slate-400">Envoyer des messages pour les anniversaires passés</p>
            </div>
            <Switch
              checked={config.birthday_filter.process_late}
              onCheckedChange={(val) => updateConfig(['birthday_filter', 'process_late'], val)}
            />
          </div>

          {config.birthday_filter.process_late && (
            <div className="space-y-2 pl-4 border-l-2 border-amber-600">
              <Label htmlFor="max_days_late">Nombre maximum de jours de retard</Label>
              <Input
                id="max_days_late"
                type="number"
                min="1"
                max="365"
                value={config.birthday_filter.max_days_late}
                onChange={(e) => updateConfig(['birthday_filter', 'max_days_late'], parseInt(e.target.value))}
                className="bg-slate-950 border-slate-800"
              />
              <p className="text-xs text-slate-400">Les anniversaires de plus de {config.birthday_filter.max_days_late} jours ne seront pas traités</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Messages */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Fichiers de messages</CardTitle>
          <CardDescription>Configurez les modèles de messages</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="messages_file">Fichier de messages (anniversaire du jour)</Label>
            <Input
              id="messages_file"
              type="text"
              value={config.messages.messages_file}
              onChange={(e) => updateConfig(['messages', 'messages_file'], e.target.value)}
              className="bg-slate-950 border-slate-800"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="late_messages_file">Fichier de messages (anniversaires en retard)</Label>
            <Input
              id="late_messages_file"
              type="text"
              value={config.messages.late_messages_file}
              onChange={(e) => updateConfig(['messages', 'late_messages_file'], e.target.value)}
              className="bg-slate-950 border-slate-800"
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="avoid_repetition">Années d'historique anti-répétition</Label>
            <Input
              id="avoid_repetition"
              type="number"
              min="0"
              max="10"
              value={config.messages.avoid_repetition_years}
              onChange={(e) => updateConfig(['messages', 'avoid_repetition_years'], parseInt(e.target.value))}
              className="bg-slate-950 border-slate-800"
            />
            <p className="text-xs text-slate-400">Éviter d'envoyer le même message pendant {config.messages.avoid_repetition_years} ans</p>
          </div>
        </CardContent>
      </Card>

      {/* Debug */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-slate-200">Débogage</CardTitle>
          <CardDescription>Options de diagnostic et logging</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="log_level">Niveau de log</Label>
            <Select
              value={config.debug.log_level}
              onValueChange={(val) => updateConfig(['debug', 'log_level'], val)}
            >
              <SelectTrigger className="bg-slate-950 border-slate-800">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="DEBUG">DEBUG (très verbeux)</SelectItem>
                <SelectItem value="INFO">INFO (normal)</SelectItem>
                <SelectItem value="WARNING">WARNING (avertissements)</SelectItem>
                <SelectItem value="ERROR">ERROR (erreurs uniquement)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Sauvegarder les captures d'écran</Label>
              <p className="text-xs text-slate-400">Utile pour le débogage mais consomme de l'espace</p>
            </div>
            <Switch
              checked={config.debug.save_screenshots}
              onCheckedChange={(val) => updateConfig(['debug', 'save_screenshots'], val)}
            />
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Sauvegarder le HTML des pages</Label>
              <p className="text-xs text-slate-400">Pour analyse approfondie (consomme beaucoup d'espace)</p>
            </div>
            <Switch
              checked={config.debug.save_html}
              onCheckedChange={(val) => updateConfig(['debug', 'save_html'], val)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end gap-3">
        <Button
          variant="outline"
          onClick={loadConfig}
          disabled={saving}
        >
          Annuler
        </Button>
        <Button
          onClick={handleSave}
          disabled={saving}
          className="bg-blue-600 hover:bg-blue-700"
        >
          {saving ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Sauvegarde...
            </>
          ) : (
            <>
              <Save className="h-4 w-4 mr-2" />
              Sauvegarder la configuration
            </>
          )}
        </Button>
      </div>
    </div>
  )
}
