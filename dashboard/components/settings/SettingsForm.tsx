"use client"

import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save, Loader2, AlertCircle, Settings, MessageSquare, Search, FileCode, Calendar } from "lucide-react"
import yaml from 'js-yaml'

// Sub-components
import { GlobalSettings } from "./GlobalSettings"
import { BirthdaySettings } from "./BirthdaySettings"
import { VisitorSettings } from "./VisitorSettings"
import { AdvancedSettings } from "./AdvancedSettings"
import { MessagesEditor } from "./MessagesEditor"
import { SchedulerSettings } from "../scheduler/SchedulerSettings"
import { ConfigData } from "./types"

export function SettingsForm() {
  const [config, setConfig] = useState<ConfigData | null>(null)
  const [yamlContent, setYamlContent] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [activeTab, setActiveTab] = useState("global")

  // Support query params for tab switching (from Overview links)
  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const tab = params.get('tab')
    if (tab && ['global', 'birthday', 'visitor', 'automation', 'advanced'].includes(tab)) {
      setActiveTab(tab)
    }
  }, [])

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
      // Deep merge with defaults could be done here, but we rely on what the API returns + UI fallbacks
      setConfig(parsed)

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
        const newYaml = yaml.dump(config, {
            indent: 2,
            lineWidth: 120,
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
          // If YAML is invalid, we don't update the object state, letting the user fix it in the YAML tab
          console.error("YAML invalid", e)
          setError("Syntaxe YAML invalide. Corrigez-la avant de revenir au mode visuel.")
      }
  }

  const handleTabChange = (value: string) => {
      if (value === "advanced") {
          syncFormToYaml()
      } else if (activeTab === "advanced" && value !== "advanced") {
          // Leaving advanced tab
          syncYamlToForm()
      }
      setActiveTab(value)
  }

  const handleSave = async () => {
    // Determine content to save based on active tab
    let contentToSave = yamlContent

    if (activeTab !== "advanced") {
        if (!config) return
        // Generate YAML from config
        try {
            contentToSave = yaml.dump(config, { indent: 2, lineWidth: 120, noRefs: true })
        } catch (e) {
             setError("Erreur lors de la génération du YAML")
             return
        }
    } else {
        // We are in advanced mode, validate YAML first
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
      await loadConfig()

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

    // Deep clone to avoid mutation
    const newConfig = JSON.parse(JSON.stringify(config))
    let current: any = newConfig

    for (let i = 0; i < path.length - 1; i++) {
        // Create path if it doesn't exist (safety for optional fields)
        if (current[path[i]] === undefined) {
             current[path[i]] = {}
        }
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
       {/* Header with Save Actions */}
      <div className="flex flex-col md:flex-row gap-4 items-start md:items-center justify-between bg-slate-900/50 p-4 rounded-lg border border-slate-800">
          <div>
              <h2 className="text-xl font-bold text-slate-100">Paramètres</h2>
              <p className="text-sm text-slate-400">Configurez le comportement de vos bots</p>
          </div>
          <div className="flex gap-3 w-full md:w-auto">
             <Button
                variant="outline"
                onClick={loadConfig}
                disabled={saving}
                className="flex-1 md:flex-none border-slate-700 hover:bg-slate-800"
             >
                Annuler
             </Button>
             <Button
                onClick={handleSave}
                disabled={saving}
                className="flex-1 md:flex-none bg-blue-600 hover:bg-blue-700"
             >
                {saving ? (
                    <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Sauvegarde...
                    </>
                ) : (
                    <>
                    <Save className="h-4 w-4 mr-2" />
                    Enregistrer
                    </>
                )}
             </Button>
          </div>
      </div>

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

      <Tabs
        value={activeTab}
        onValueChange={handleTabChange}
        orientation="vertical"
        className="flex flex-col md:flex-row gap-6"
      >
        {/* Vertical Navigation */}
        <TabsList className="flex md:flex-col h-auto bg-transparent space-y-0 md:space-y-2 space-x-2 md:space-x-0 overflow-x-auto md:overflow-visible p-1 justify-start md:w-64 min-w-[200px]">
            <TabsTrigger
                value="global"
                className="w-full justify-start gap-2 px-4 py-3 data-[state=active]:bg-slate-800 data-[state=active]:text-blue-400 border border-transparent data-[state=active]:border-slate-700"
            >
                <Settings className="h-4 w-4" />
                Global Settings
            </TabsTrigger>
            <TabsTrigger
                value="birthday"
                className="w-full justify-start gap-2 px-4 py-3 data-[state=active]:bg-slate-800 data-[state=active]:text-pink-400 border border-transparent data-[state=active]:border-slate-700"
            >
                <MessageSquare className="h-4 w-4" />
                Birthday Bot
            </TabsTrigger>
            <TabsTrigger
                value="visitor"
                className="w-full justify-start gap-2 px-4 py-3 data-[state=active]:bg-slate-800 data-[state=active]:text-emerald-400 border border-transparent data-[state=active]:border-slate-700"
            >
                <Search className="h-4 w-4" />
                Visitor Bot
            </TabsTrigger>
            <TabsTrigger
                value="automation"
                className="w-full justify-start gap-2 px-4 py-3 data-[state=active]:bg-slate-800 data-[state=active]:text-cyan-400 border border-transparent data-[state=active]:border-slate-700"
            >
                <Calendar className="h-4 w-4" />
                Automation
            </TabsTrigger>
            <TabsTrigger
                value="advanced"
                className="w-full justify-start gap-2 px-4 py-3 data-[state=active]:bg-slate-800 data-[state=active]:text-amber-400 border border-transparent data-[state=active]:border-slate-700 mt-auto"
            >
                <FileCode className="h-4 w-4" />
                Advanced (YAML)
            </TabsTrigger>
        </TabsList>

        {/* Content Area */}
        <div className="flex-1 min-w-0">
            <TabsContent value="global" className="mt-0 space-y-6">
                <GlobalSettings config={config} updateConfig={updateConfig} />
            </TabsContent>

            <TabsContent value="birthday" className="mt-0 space-y-6">
                <BirthdaySettings config={config} updateConfig={updateConfig} />
                <MessagesEditor />
            </TabsContent>

            <TabsContent value="visitor" className="mt-0 space-y-6">
                <VisitorSettings config={config} updateConfig={updateConfig} />
            </TabsContent>

            <TabsContent value="automation" className="mt-0 space-y-6">
                <SchedulerSettings />
            </TabsContent>

            <TabsContent value="advanced" className="mt-0">
                <AdvancedSettings yamlContent={yamlContent} setYamlContent={setYamlContent} />
            </TabsContent>
        </div>
      </Tabs>
    </div>
  )
}
