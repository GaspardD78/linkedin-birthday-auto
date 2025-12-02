"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save, Loader2, AlertCircle, FileCode, Sliders } from "lucide-react"
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
  visitor: {
    enabled: boolean
    keywords: string[]
    location: string
    limits: {
      profiles_per_run: number
      max_pages_to_scrape: number
      max_pages_without_new: number
    }
    delays: {
      min_seconds: number
      max_seconds: number
      profile_visit_min: number
      profile_visit_max: number
      page_navigation_min: number
      page_navigation_max: number
    }
    retry: {
      max_attempts: number
      backoff_factor: number
    }
  }
  debug: {
    log_level: string
    save_screenshots: boolean
    save_html: boolean
  }
}

export function SettingsForm() {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [yamlContent, setYamlContent] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [activeTab, setActiveTab] = useState("form")

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
      // Store raw content for YAML view
      setYamlContent(data.content)

      // Parse for Form view
      const parsed = yaml.load(data.content) as any
      setConfig({
        bot_mode: parsed.bot_mode || 'standard',
        dry_run: parsed.dry_run || false,
        messaging_limits: parsed.messaging_limits || {},
        scheduling: parsed.scheduling || {},
        delays: parsed.delays || {},
        birthday_filter: parsed.birthday_filter || {},
        messages: parsed.messages || {},
        visitor: parsed.visitor || {
          enabled: true,
          keywords: [],
          location: 'France',
          limits: {
            profiles_per_run: 15,
            max_pages_to_scrape: 100,
            max_pages_without_new: 3
          },
          delays: {
            min_seconds: 8,
            max_seconds: 20,
            profile_visit_min: 15,
            profile_visit_max: 35,
            page_navigation_min: 3,
            page_navigation_max: 6
          },
          retry: {
            max_attempts: 3,
            backoff_factor: 2
          }
        },
        debug: parsed.debug || {}
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config')
    } finally {
      setLoading(false)
    }
  }

  // Sync Form -> YAML when switching to YAML tab or saving from Form
  const syncFormToYaml = () => {
    if (!config) return
    try {
        // We preserve the existing structure by merging, but here we just dump the current config state
        // To be safer, we should probably merge with original if there are extra fields,
        // but for now we assume config covers all we care about.
        const newYaml = yaml.dump(config, {
            indent: 2,
            lineWidth: 80,
            noRefs: true
        })
        setYamlContent(newYaml)
    } catch (e) {
        console.error("Failed to sync form to YAML", e)
    }
  }

  // Sync YAML -> Form when switching to Form tab
  const syncYamlToForm = () => {
      try {
          const parsed = yaml.load(yamlContent) as any
          setConfig(prev => ({
              ...prev,
              ...parsed
          }))
          setError(null)
      } catch (e) {
          setError("Erreur de syntaxe YAML. Veuillez corriger avant de revenir au formulaire.")
          // Prevent switching tab effectively or just show error?
          // We'll let the error state handle it
      }
  }

  const handleTabChange = (value: string) => {
      if (value === "yaml") {
          syncFormToYaml()
      } else if (value === "form") {
          syncYamlToForm()
      }
      setActiveTab(value)
  }

  const validateConfig = (): string | null => {
    if (activeTab === "yaml") {
        try {
            yaml.load(yamlContent)
            return null
        } catch (e) {
            return "Syntaxe YAML invalide"
        }
    }

    if (!config) return null

    // Validate messaging_limits.weekly_message_limit
    if (config.messaging_limits?.weekly_message_limit) {
      const value = config.messaging_limits.weekly_message_limit
      if (value < 1 || value > 2000) {
        return 'Limite hebdomadaire doit être entre 1 et 2000'
      }
    }

    // Validate delays.min_delay_seconds
    if (config.delays?.min_delay_seconds) {
      const value = config.delays.min_delay_seconds
      if (value < 30 || value > 3600) {
        return 'Délai min entre messages doit être entre 30 et 3600 secondes'
      }
    }

    // ... (Keep other validations if needed, or rely on server-side/pydantic)

    return null
  }

  const handleSave = async () => {
    // Sync first if in Form mode
    let contentToSave = yamlContent
    if (activeTab === "form") {
        if (!config) return
        const validationError = validateConfig()
        if (validationError) {
            setError(validationError)
            return
        }
        // Generate YAML from config
        contentToSave = yaml.dump(config, { indent: 2, lineWidth: 80, noRefs: true })
    } else {
        // Validate YAML
        try {
            yaml.load(contentToSave)
        } catch (e) {
            setError("Syntaxe YAML invalide")
            return
        }
    }

    setSaving(true)
    setError(null)
    setSuccess(false)

    try {
      const res = await fetch('/api/settings/yaml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: contentToSave })
      })

      if (!res.ok) throw new Error('Failed to save config')

      // Reload to ensure everything is in sync
      if (activeTab === "form") {
          // If we saved from form, we might want to reload to get any server-side formatting,
          // but for UX speed we can just update local state if needed.
          // Let's reload to be safe and update both views.
           await loadConfig()
      } else {
          // If we saved YAML, we must reload to update the Form view state
           await loadConfig()
      }

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

      <Tabs value={activeTab} onValueChange={handleTabChange} className="w-full">
        <div className="flex items-center justify-between mb-4">
            <TabsList className="bg-slate-900 border border-slate-800">
                <TabsTrigger value="form" className="data-[state=active]:bg-slate-800">
                    <Sliders className="h-4 w-4 mr-2" />
                    Assistant Visuel
                </TabsTrigger>
                <TabsTrigger value="yaml" className="data-[state=active]:bg-slate-800">
                    <FileCode className="h-4 w-4 mr-2" />
                    Éditeur Avancé (YAML)
                </TabsTrigger>
            </TabsList>

            <div className="flex gap-3">
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
                    Sauvegarder
                    </>
                )}
                </Button>
            </div>
        </div>

        <TabsContent value="form" className="space-y-6 mt-0">
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

            {/* Limites d&apos;envoi */}
            <Card className="bg-slate-900 border-slate-800">
                <CardHeader>
                <CardTitle className="text-slate-200">Limites d&apos;envoi de messages</CardTitle>
                <CardDescription>Contrôlez le volume d&apos;envoi pour éviter les restrictions LinkedIn</CardDescription>
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
                        max="2000"
                        value={config.messaging_limits.weekly_message_limit}
                        onChange={(e) => updateConfig(['messaging_limits', 'weekly_message_limit'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                    {config.messaging_limits.weekly_message_limit > 100 && (
                        <div className="flex items-start gap-2 p-2 bg-amber-950/50 border border-amber-700 rounded text-xs text-amber-300">
                        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <span>⚠️ LinkedIn recommande &lt; 100 messages/semaine pour éviter les restrictions</span>
                        </div>
                    )}
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
                <CardDescription>Définissez les heures d&apos;activité du bot</CardDescription>
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
                        max="3600"
                        value={config.delays.min_delay_seconds}
                        onChange={(e) => updateConfig(['delays', 'min_delay_seconds'], parseInt(e.target.value))}
                        className="bg-slate-950 border-slate-800"
                    />
                    {config.delays.min_delay_seconds < 120 && (
                        <div className="flex items-start gap-2 p-2 bg-amber-950/50 border border-amber-700 rounded text-xs text-amber-300">
                        <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                        <span>⚠️ Recommandé : &ge; 120 secondes (2 min) pour simuler un comportement humain</span>
                        </div>
                    )}
                    </div>

                    <div className="space-y-2">
                    <Label htmlFor="max_delay">Délai maximum (secondes)</Label>
                    <Input
                        id="max_delay"
                        type="number"
                        min="60"
                        max="7200"
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
                    <p className="text-xs text-slate-400">Envoyer des messages pour les anniversaires d&apos;aujourd&apos;hui</p>
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

            {/* Configuration Visite de Profils */}
            <Card className="bg-slate-900 border-slate-800 border-blue-600/50">
                <CardHeader>
                <CardTitle className="text-slate-200 flex items-center gap-2">
                    🔍 Configuration Visite de Profils
                    <span className="text-xs bg-blue-600/20 text-blue-400 px-2 py-1 rounded">Visitor Bot</span>
                </CardTitle>
                <CardDescription>Paramètres pour la visite automatique de profils LinkedIn</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                {/* Activation */}
                <div className="flex items-center justify-between">
                    <div className="space-y-0.5">
                    <Label>Activer la visite de profils</Label>
                    <p className="text-xs text-slate-400">Active ou désactive le bot de visite de profils</p>
                    </div>
                    <Switch
                    checked={config.visitor.enabled}
                    onCheckedChange={(val) => updateConfig(['visitor', 'enabled'], val)}
                    />
                </div>

                {config.visitor.enabled && (
                    <>
                    {/* Keywords et Location */}
                    <div className="space-y-4 p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <div className="space-y-2">
                        <Label htmlFor="visitor_keywords">Mots-clés de recherche</Label>
                        <Input
                            id="visitor_keywords"
                            type="text"
                            value={config.visitor.keywords.join(', ')}
                            onChange={(e) => updateConfig(['visitor', 'keywords'], e.target.value.split(',').map(k => k.trim()).filter(k => k))}
                            placeholder="python, developer, engineer"
                            className="bg-slate-900 border-slate-700"
                        />
                        <p className="text-xs text-slate-400">Séparez les mots-clés par des virgules</p>
                        </div>

                        <div className="space-y-2">
                        <Label htmlFor="visitor_location">Localisation</Label>
                        <Input
                            id="visitor_location"
                            type="text"
                            value={config.visitor.location}
                            onChange={(e) => updateConfig(['visitor', 'location'], e.target.value)}
                            placeholder="France"
                            className="bg-slate-900 border-slate-700"
                        />
                        <p className="text-xs text-slate-400">Pays ou région pour la recherche</p>
                        </div>
                    </div>

                    {/* Limites */}
                    <div className="space-y-4 p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <h4 className="font-semibold text-slate-300 text-sm">Limites de visite</h4>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="profiles_per_run">Profils par exécution</Label>
                            <Input
                            id="profiles_per_run"
                            type="number"
                            min="1"
                            max="500"
                            value={config.visitor.limits.profiles_per_run}
                            onChange={(e) => updateConfig(['visitor', 'limits', 'profiles_per_run'], parseInt(e.target.value))}
                            className="bg-slate-900 border-slate-700"
                            />
                            {config.visitor.limits.profiles_per_run > 50 && (
                            <div className="flex items-start gap-2 p-2 bg-amber-950/50 border border-amber-700 rounded text-xs text-amber-300">
                                <AlertCircle className="h-4 w-4 flex-shrink-0 mt-0.5" />
                                <span>⚠️ Recommandé : &le; 50 profils/jour pour éviter détection LinkedIn</span>
                            </div>
                            )}
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="max_pages_scrape">Pages max à scraper</Label>
                            <Input
                            id="max_pages_scrape"
                            type="number"
                            min="1"
                            max="2000"
                            value={config.visitor.limits.max_pages_to_scrape}
                            onChange={(e) => updateConfig(['visitor', 'limits', 'max_pages_to_scrape'], parseInt(e.target.value))}
                            className="bg-slate-900 border-slate-700"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="max_pages_without_new">Pages sans nouveaux profils</Label>
                            <Input
                            id="max_pages_without_new"
                            type="number"
                            min="1"
                            max="50"
                            value={config.visitor.limits.max_pages_without_new}
                            onChange={(e) => updateConfig(['visitor', 'limits', 'max_pages_without_new'], parseInt(e.target.value))}
                            className="bg-slate-900 border-slate-700"
                            />
                        </div>
                        </div>
                    </div>

                    {/* Délais */}
                    <div className="space-y-4 p-4 bg-slate-950 rounded-lg border border-slate-800">
                        <h4 className="font-semibold text-slate-300 text-sm">Délais entre actions</h4>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="space-y-2">
                            <Label htmlFor="visit_min_delay">Délai min général (s)</Label>
                            <Input
                            id="visit_min_delay"
                            type="number"
                            min="1"
                            max="300"
                            value={config.visitor.delays.min_seconds}
                            onChange={(e) => updateConfig(['visitor', 'delays', 'min_seconds'], parseInt(e.target.value))}
                            className="bg-slate-900 border-slate-700"
                            />
                        </div>

                        <div className="space-y-2">
                            <Label htmlFor="visit_max_delay">Délai max général (s)</Label>
                            <Input
                            id="visit_max_delay"
                            type="number"
                            min="5"
                            max="600"
                            value={config.visitor.delays.max_seconds}
                            onChange={(e) => updateConfig(['visitor', 'delays', 'max_seconds'], parseInt(e.target.value))}
                            className="bg-slate-900 border-slate-700"
                            />
                        </div>
                        </div>
                    </div>
                    </>
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
                </CardContent>
            </Card>
        </TabsContent>

        <TabsContent value="yaml" className="mt-0">
            <Card className="bg-slate-900 border-slate-800 h-[calc(100vh-250px)]">
                <CardHeader>
                    <CardTitle className="text-slate-200">Éditeur Configuration Avancée</CardTitle>
                    <CardDescription>Modifiez directement le fichier config.yaml. Attention : respectez la syntaxe YAML.</CardDescription>
                </CardHeader>
                <CardContent className="h-full pb-16">
                    <Textarea
                        className="h-full font-mono text-sm bg-slate-950 border-slate-800 focus-visible:ring-emerald-500"
                        value={yamlContent}
                        onChange={(e) => setYamlContent(e.target.value)}
                        spellCheck={false}
                    />
                </CardContent>
            </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
