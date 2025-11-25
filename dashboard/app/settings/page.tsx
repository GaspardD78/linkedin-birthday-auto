"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Save, RefreshCw } from "lucide-react"

export default function SettingsPage() {
  const [configYaml, setConfigYaml] = useState("")
  const [messages, setMessages] = useState("")
  const [loading, setLoading] = useState(false)

  // Charger les configurations au montage
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    try {
      const [yamlRes, msgRes] = await Promise.all([
        fetch('/api/settings/yaml'),
        fetch('/api/settings/messages')
      ])

      if (yamlRes.ok) {
        const data = await yamlRes.json()
        setConfigYaml(data.content)
      }
      if (msgRes.ok) {
        const data = await msgRes.json()
        setMessages(data.content)
      }
    } catch (error) {
      console.error("Erreur chargement config:", error)
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async (type: 'yaml' | 'messages', content: string) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/settings/${type}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      })

      if (res.ok) {
        alert("Sauvegardé avec succès !")
      } else {
        alert("Erreur lors de la sauvegarde.")
      }
    } catch (error) {
      alert("Erreur réseau.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white">Paramètres</h1>
        <Button variant="outline" onClick={fetchConfig} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      <Tabs defaultValue="general" className="w-full">
        <TabsList className="bg-slate-900 border border-slate-800">
          <TabsTrigger value="general">Configuration (YAML)</TabsTrigger>
          <TabsTrigger value="messages">Messages (TXT)</TabsTrigger>
        </TabsList>

        {/* Éditeur YAML */}
        <TabsContent value="general">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-slate-200">Configuration du Bot</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={configYaml}
                onChange={(e) => setConfigYaml(e.target.value)}
                className="font-mono text-xs h-[500px] bg-slate-950 border-slate-800 text-slate-300"
                spellCheck={false}
              />
              <Button onClick={() => saveConfig('yaml', configYaml)} disabled={loading} className="bg-blue-600 hover:bg-blue-700">
                <Save className="h-4 w-4 mr-2" /> Sauvegarder Config
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* Éditeur Messages */}
        <TabsContent value="messages">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-slate-200">Modèles de Messages</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-400">Un message par ligne. Utilisez {'{name}'} pour le prénom.</p>
              <Textarea
                value={messages}
                onChange={(e) => setMessages(e.target.value)}
                className="font-mono text-sm h-[500px] bg-slate-950 border-slate-800 text-slate-300"
                placeholder="Joyeux anniversaire {name} !..."
              />
              <Button onClick={() => saveConfig('messages', messages)} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
                <Save className="h-4 w-4 mr-2" /> Sauvegarder Messages
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
