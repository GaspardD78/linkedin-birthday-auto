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
import { Bell, Mail, AlertCircle, CheckCircle2, Save, TestTube } from "lucide-react"

interface NotificationSettings {
  email_enabled: boolean
  email_address: string
  notify_on_error: boolean
  notify_on_success: boolean
  notify_on_bot_start: boolean
  notify_on_bot_stop: boolean
  notify_on_cookies_expiry: boolean
}

export default function NotificationsPage() {
  const [settings, setSettings] = useState<NotificationSettings>({
    email_enabled: false,
    email_address: "",
    notify_on_error: true,
    notify_on_success: false,
    notify_on_bot_start: false,
    notify_on_bot_stop: false,
    notify_on_cookies_expiry: true,
  })
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    fetchSettings()
  }, [])

  const fetchSettings = async () => {
    try {
      const response = await fetch('/api/notifications/settings')
      if (response.ok) {
        const data = await response.json()
        setSettings(data)
      }
    } catch (error) {
      console.error('Failed to fetch notification settings:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const response = await fetch('/api/notifications/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(settings)
      })

      if (!response.ok) throw new Error('Failed to save settings')

      toast({
        title: "Paramètres sauvegardés",
        description: "Les notifications ont été configurées"
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

  const handleTest = async () => {
    setTesting(true)
    try {
      const response = await fetch('/api/notifications/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: settings.email_address })
      })

      if (!response.ok) throw new Error('Failed to send test notification')

      toast({
        title: "Notification test envoyée",
        description: "Vérifiez votre boîte mail"
      })
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setTesting(false)
    }
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
          { label: "Notifications" }
        ]}
      />

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Notifications</h1>
        <p className="text-muted-foreground mt-2">
          Configurez les alertes pour rester informé des événements importants.
        </p>
      </div>

      {/* Email Configuration */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5 text-blue-500" />
            Configuration Email
          </CardTitle>
          <CardDescription>
            Recevez des notifications par email en cas d'événement important
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label htmlFor="email-enabled">Activer les notifications email</Label>
              <p className="text-xs text-slate-500">
                Envoyer des emails pour les événements configurés ci-dessous
              </p>
            </div>
            <Switch
              id="email-enabled"
              checked={settings.email_enabled}
              onCheckedChange={(checked) => setSettings({ ...settings, email_enabled: checked })}
            />
          </div>

          {settings.email_enabled && (
            <>
              <div className="space-y-2">
                <Label htmlFor="email-address">Adresse email</Label>
                <div className="flex gap-2">
                  <Input
                    id="email-address"
                    type="email"
                    placeholder="votre.email@example.com"
                    value={settings.email_address}
                    onChange={(e) => setSettings({ ...settings, email_address: e.target.value })}
                    className="bg-slate-950 border-slate-700"
                  />
                  <Button
                    variant="outline"
                    onClick={handleTest}
                    disabled={!settings.email_address || testing}
                    className="gap-2"
                  >
                    <TestTube className="h-4 w-4" />
                    {testing ? "Envoi..." : "Test"}
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Event Types */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-5 w-5 text-cyan-500" />
            Types d'Alertes
          </CardTitle>
          <CardDescription>
            Sélectionnez les événements pour lesquels vous souhaitez être notifié
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-red-500" />
              <div>
                <Label htmlFor="notify-error" className="cursor-pointer">Erreurs critiques</Label>
                <p className="text-xs text-slate-500">Échecs d'exécution, erreurs API, etc.</p>
              </div>
            </div>
            <Switch
              id="notify-error"
              checked={settings.notify_on_error}
              onCheckedChange={(checked) => setSettings({ ...settings, notify_on_error: checked })}
            />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="flex items-center gap-3">
              <CheckCircle2 className="h-5 w-5 text-emerald-500" />
              <div>
                <Label htmlFor="notify-success" className="cursor-pointer">Exécutions réussies</Label>
                <p className="text-xs text-slate-500">Confirmation après chaque run réussi</p>
              </div>
            </div>
            <Switch
              id="notify-success"
              checked={settings.notify_on_success}
              onCheckedChange={(checked) => setSettings({ ...settings, notify_on_success: checked })}
            />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-blue-500" />
              <div>
                <Label htmlFor="notify-start" className="cursor-pointer">Démarrage des bots</Label>
                <p className="text-xs text-slate-500">Notification lors du lancement d'un bot</p>
              </div>
            </div>
            <Switch
              id="notify-start"
              checked={settings.notify_on_bot_start}
              onCheckedChange={(checked) => setSettings({ ...settings, notify_on_bot_start: checked })}
            />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="flex items-center gap-3">
              <Bell className="h-5 w-5 text-slate-500" />
              <div>
                <Label htmlFor="notify-stop" className="cursor-pointer">Arrêt des bots</Label>
                <p className="text-xs text-slate-500">Notification lors de l'arrêt d'un bot</p>
              </div>
            </div>
            <Switch
              id="notify-stop"
              checked={settings.notify_on_bot_stop}
              onCheckedChange={(checked) => setSettings({ ...settings, notify_on_bot_stop: checked })}
            />
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-5 w-5 text-amber-500" />
              <div>
                <Label htmlFor="notify-cookies" className="cursor-pointer">Cookies expirés</Label>
                <p className="text-xs text-slate-500">Alerte quand les cookies LinkedIn expirent</p>
              </div>
            </div>
            <Switch
              id="notify-cookies"
              checked={settings.notify_on_cookies_expiry}
              onCheckedChange={(checked) => setSettings({ ...settings, notify_on_cookies_expiry: checked })}
            />
          </div>
        </CardContent>
      </Card>

      {/* Save Button */}
      <div className="flex justify-end gap-4">
        <Button
          variant="default"
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

      {/* Info Banner */}
      <div className="p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
        <h3 className="text-sm font-semibold text-blue-400 mb-2">💡 Conseils</h3>
        <ul className="text-xs text-blue-200/80 space-y-1 list-disc list-inside">
          <li>Activez au minimum les notifications d'erreur pour être alerté rapidement</li>
          <li>Testez la configuration email pour vérifier que tout fonctionne</li>
          <li>Les notifications sont également affichées dans le dashboard en temps réel</li>
        </ul>
      </div>
    </div>
  )
}
