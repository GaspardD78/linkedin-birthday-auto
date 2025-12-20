"use client"

import { useState, useEffect } from "react"
import { Breadcrumbs } from "@/components/ui/breadcrumbs"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { Badge } from "@/components/ui/badge"
import { useToast } from "@/components/ui/use-toast"
import { Webhook, Plus, Trash2, Save, TestTube, Copy, CheckCircle2 } from "lucide-react"

interface WebhookConfig {
  id: string
  url: string
  enabled: boolean
  events: string[]
  secret?: string
}

export default function WebhooksPage() {
  const [webhooks, setWebhooks] = useState<WebhookConfig[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  const eventTypes = [
    { id: 'bot_started', label: 'Bot démarré', color: 'blue' },
    { id: 'bot_stopped', label: 'Bot arrêté', color: 'slate' },
    { id: 'bot_completed', label: 'Exécution terminée', color: 'emerald' },
    { id: 'bot_error', label: 'Erreur', color: 'red' },
    { id: 'cookies_expired', label: 'Cookies expirés', color: 'amber' },
  ]

  useEffect(() => {
    fetchWebhooks()
  }, [])

  const fetchWebhooks = async () => {
    try {
      const response = await fetch('/api/webhooks')
      if (response.ok) {
        const data = await response.json()
        setWebhooks(data.webhooks || [])
      }
    } catch (error) {
    } finally {
      setLoading(false)
    }
  }

  const handleAddWebhook = () => {
    const newWebhook: WebhookConfig = {
      id: `webhook-${Date.now()}`,
      url: '',
      enabled: true,
      events: ['bot_error'],
      secret: generateSecret()
    }
    setWebhooks([...webhooks, newWebhook])
  }

  const handleRemoveWebhook = (id: string) => {
    setWebhooks(webhooks.filter(w => w.id !== id))
  }

  const handleUpdateWebhook = (id: string, updates: Partial<WebhookConfig>) => {
    setWebhooks(webhooks.map(w => w.id === id ? { ...w, ...updates } : w))
  }

  const handleToggleEvent = (webhookId: string, eventId: string) => {
    const webhook = webhooks.find(w => w.id === webhookId)
    if (!webhook) return

    const events = webhook.events.includes(eventId)
      ? webhook.events.filter(e => e !== eventId)
      : [...webhook.events, eventId]

    handleUpdateWebhook(webhookId, { events })
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/webhooks', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhooks })
      })

      if (!response.ok) throw new Error('Failed to save webhooks')

      toast({
        title: "Webhooks sauvegardés",
        description: "Les webhooks ont été configurés"
      })
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setSaving(false)
    }
  }

  const handleTest = async (webhookId: string) => {
    try {
      const webhook = webhooks.find(w => w.id === webhookId)
      if (!webhook) return

      const response = await fetch('/api/webhooks/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook })
      })

      if (!response.ok) throw new Error('Failed to test webhook')

      toast({
        title: "Webhook testé",
        description: "Vérifiez votre endpoint"
      })
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    }
  }

  const generateSecret = () => {
    return 'whsec_' + Math.random().toString(36).substring(2, 15) + Math.random().toString(36).substring(2, 15)
  }

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text)
    toast({
      title: "Copié",
      description: "Le secret a été copié dans le presse-papier"
    })
  }

  if (loading) {
    return (
      <div className="container mx-auto py-8">
        <div className="h-96 bg-slate-800/50 rounded animate-pulse"></div>
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      <Breadcrumbs
        items={[
          { label: "Paramètres", href: "/settings" },
          { label: "Webhooks" }
        ]}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Webhooks</h1>
          <p className="text-muted-foreground mt-2">
            Configurez des webhooks pour automatiser vos workflows externes.
          </p>
        </div>
        <Button onClick={handleAddWebhook} className="gap-2 bg-cyan-600 hover:bg-cyan-700">
          <Plus className="h-4 w-4" />
          Ajouter un webhook
        </Button>
      </div>

      {/* Webhooks List */}
      <div className="space-y-4">
        {webhooks.length === 0 ? (
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="py-12 text-center">
              <Webhook className="h-12 w-12 mx-auto mb-4 text-slate-600" />
              <p className="text-slate-400 mb-4">Aucun webhook configuré</p>
              <Button onClick={handleAddWebhook} variant="outline" className="gap-2">
                <Plus className="h-4 w-4" />
                Créer votre premier webhook
              </Button>
            </CardContent>
          </Card>
        ) : (
          webhooks.map((webhook) => (
            <Card key={webhook.id} className="bg-slate-900 border-slate-800">
              <CardHeader>
                <div className="flex items-center justify-between">
                  <CardTitle className="flex items-center gap-2 text-lg">
                    <Webhook className="h-5 w-5 text-cyan-500" />
                    Webhook {webhook.id.split('-')[1]}
                  </CardTitle>
                  <div className="flex items-center gap-2">
                    <Switch
                      checked={webhook.enabled}
                      onCheckedChange={(checked) => handleUpdateWebhook(webhook.id, { enabled: checked })}
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleRemoveWebhook(webhook.id)}
                      className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* URL */}
                <div className="space-y-2">
                  <Label>URL du webhook</Label>
                  <div className="flex gap-2">
                    <Input
                      type="url"
                      placeholder="https://votre-endpoint.com/webhook"
                      value={webhook.url}
                      onChange={(e) => handleUpdateWebhook(webhook.id, { url: e.target.value })}
                      className="bg-slate-950 border-slate-700"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTest(webhook.id)}
                      disabled={!webhook.url}
                      className="gap-2"
                    >
                      <TestTube className="h-4 w-4" />
                      Test
                    </Button>
                  </div>
                </div>

                {/* Secret */}
                <div className="space-y-2">
                  <Label>Secret (pour vérifier la signature)</Label>
                  <div className="flex gap-2">
                    <Input
                      type="text"
                      value={webhook.secret || ''}
                      readOnly
                      className="bg-slate-950 border-slate-700 font-mono text-xs"
                    />
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(webhook.secret || '')}
                      className="gap-2"
                    >
                      <Copy className="h-4 w-4" />
                    </Button>
                  </div>
                </div>

                {/* Events */}
                <div className="space-y-2">
                  <Label>Événements déclencheurs</Label>
                  <div className="flex flex-wrap gap-2">
                    {eventTypes.map((event) => (
                      <Badge
                        key={event.id}
                        variant={webhook.events.includes(event.id) ? "default" : "outline"}
                        className={`cursor-pointer transition-all ${
                          webhook.events.includes(event.id)
                            ? `bg-${event.color}-600 hover:bg-${event.color}-700`
                            : 'hover:bg-slate-800'
                        }`}
                        onClick={() => handleToggleEvent(webhook.id, event.id)}
                      >
                        {webhook.events.includes(event.id) && <CheckCircle2 className="h-3 w-3 mr-1" />}
                        {event.label}
                      </Badge>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Save Button */}
      {webhooks.length > 0 && (
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={saving}
            className="gap-2 bg-cyan-600 hover:bg-cyan-700"
          >
            {saving ? (
              <>
                <Save className="h-4 w-4 animate-spin" />
                Sauvegarde...
              </>
            ) : (
              <>
                <Save className="h-4 w-4" />
                Sauvegarder
              </>
            )}
          </Button>
        </div>
      )}

      {/* Documentation */}
      <Card className="bg-blue-500/10 border-blue-500/30">
        <CardHeader>
          <CardTitle className="text-sm text-blue-400">📚 Format des données</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <p className="text-xs text-blue-200/80">
            Les webhooks reçoivent un payload JSON avec la structure suivante :
          </p>
          <pre className="text-xs bg-slate-950 p-4 rounded border border-slate-700 overflow-x-auto">
{`{
  "event": "bot_completed",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "bot_type": "birthday",
    "messages_sent": 10,
    "errors": 0
  },
  "signature": "sha256=..."
}`}
          </pre>
        </CardContent>
      </Card>
    </div>
  )
}
