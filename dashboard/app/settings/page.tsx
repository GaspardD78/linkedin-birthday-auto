"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Textarea } from "@/components/ui/textarea"
import { Save, RefreshCw } from "lucide-react"
import { SettingsForm } from "@/components/settings/SettingsForm"
import { PageNavigation } from "@/components/layout/PageNavigation"

export default function SettingsPage() {
  const [configYaml, setConfigYaml] = useState("")
  const [messages, setMessages] = useState("")
  const [lateMessages, setLateMessages] = useState("")
  const [loading, setLoading] = useState(false)

  // Charger les configurations au montage
  useEffect(() => {
    fetchConfig()
  }, [])

  const fetchConfig = async () => {
    setLoading(true)
    try {
      const [yamlRes, msgRes, lateMsgRes] = await Promise.all([
        fetch('/api/settings/yaml'),
        fetch('/api/settings/messages'),
        fetch('/api/settings/late-messages')
      ])

      if (yamlRes.ok) {
        const data = await yamlRes.json()
        setConfigYaml(data.content)
      }
      if (msgRes.ok) {
        const data = await msgRes.json()
        setMessages(data.content)
      }
      if (lateMsgRes.ok) {
        const data = await lateMsgRes.json()
        setLateMessages(data.content)
      }
    } catch (error) {
      console.error("Erreur chargement config:", error)
    } finally {
      setLoading(false)
    }
  }

  const saveConfig = async (type: 'yaml' | 'messages' | 'late-messages', content: string) => {
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
    <div className="space-y-6">
      <PageNavigation
        title="Paramètres"
        description="Configuration du bot et des messages"
        showBackButton={false}
      />

      <div className="flex justify-end">
        <Button variant="outline" onClick={fetchConfig} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
          Actualiser
        </Button>
      </div>

      <Tabs defaultValue="form" className="w-full">
        <TabsList className="bg-slate-900 border border-slate-800">
          <TabsTrigger value="form">Configuration</TabsTrigger>
          <TabsTrigger value="messages">Messages</TabsTrigger>
          <TabsTrigger value="advanced">Avancé (YAML)</TabsTrigger>
        </TabsList>

        {/* Formulaire de configuration */}
        <TabsContent value="form">
          <SettingsForm />
        </TabsContent>

        {/* Éditeur YAML */}
        <TabsContent value="advanced">
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
        <TabsContent value="messages" className="space-y-6">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-slate-200">Messages d'anniversaire du jour</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-400">Un message par ligne. Utilisez {'{name}'} pour le prénom.</p>
              <Textarea
                value={messages}
                onChange={(e) => setMessages(e.target.value)}
                className="font-mono text-sm h-[400px] bg-slate-950 border-slate-800 text-slate-300"
                placeholder="Joyeux anniversaire {name} !&#10;Happy birthday {name}! 🎂&#10;Bon anniversaire {name} !"
              />
              <Button onClick={() => saveConfig('messages', messages)} disabled={loading} className="bg-emerald-600 hover:bg-emerald-700">
                <Save className="h-4 w-4 mr-2" /> Sauvegarder Messages du jour
              </Button>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800 border-amber-600/50">
            <CardHeader>
              <CardTitle className="text-slate-200 flex items-center gap-2">
                Messages d'anniversaire en retard
                <span className="text-xs bg-amber-600/20 text-amber-400 px-2 py-1 rounded">En retard</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-slate-400">
                Un message par ligne. Utilisez {'{name}'} pour le prénom et {'{days}'} pour le nombre de jours de retard.
              </p>
              <Textarea
                value={lateMessages}
                onChange={(e) => setLateMessages(e.target.value)}
                className="font-mono text-sm h-[400px] bg-slate-950 border-slate-800 text-slate-300"
                placeholder="Bon anniversaire en retard {name} ! J'espère que tu as passé une excellente journée il y a {days} jours !&#10;Happy belated birthday {name}! 🎂&#10;Joyeux anniversaire (avec {days} jours de retard) {name} !"
              />
              <Button onClick={() => saveConfig('late-messages', lateMessages)} disabled={loading} className="bg-amber-600 hover:bg-amber-700">
                <Save className="h-4 w-4 mr-2" /> Sauvegarder Messages en retard
              </Button>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
