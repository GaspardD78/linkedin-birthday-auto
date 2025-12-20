"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Save, Loader2, RefreshCw } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function MessagesEditor() {
  const [messages, setMessages] = useState("")
  const [lateMessages, setLateMessages] = useState("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    loadMessages()
  }, [])

  const loadMessages = async () => {
    setLoading(true)
    try {
      const [msgRes, lateRes] = await Promise.all([
        fetch('/api/settings/messages'),
        fetch('/api/settings/late-messages')
      ])

      if (msgRes.ok) {
        const data = await msgRes.json()
        setMessages(data.content)
      }

      if (lateRes.ok) {
        const data = await lateRes.json()
        setLateMessages(data.content)
      }
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: "Impossible de charger les messages"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async (type: 'standard' | 'late') => {
    setSaving(true)
    try {
      const endpoint = type === 'standard' ? '/api/settings/messages' : '/api/settings/late-messages'
      const content = type === 'standard' ? messages : lateMessages

      const res = await fetch(endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      })

      if (!res.ok) throw new Error('Failed to save')

      toast({
        title: "Succès",
        description: "Messages sauvegardés avec succès"
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: "Impossible de sauvegarder les messages"
      })
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center p-8">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <Tabs defaultValue="standard" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="standard">Messages Anniversaire</TabsTrigger>
          <TabsTrigger value="late">Messages Retard</TabsTrigger>
        </TabsList>

        <TabsContent value="standard" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Messages d&apos;anniversaire</CardTitle>
              <CardDescription>
                Un message par ligne. Le bot choisira aléatoirement un message.
                Utilisez {"{name}"} pour insérer le prénom.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={messages}
                onChange={(e) => setMessages(e.target.value)}
                className="min-h-[400px] font-mono text-sm"
                placeholder="Joyeux anniversaire {name} !&#10;Bon anniversaire {name} !&#10;..."
              />
              <div className="flex justify-between">
                <Button variant="outline" onClick={loadMessages}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Recharger
                </Button>
                <Button onClick={() => handleSave('standard')} disabled={saving}>
                  {saving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  Sauvegarder
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="late" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Messages de retard</CardTitle>
              <CardDescription>
                Messages pour les anniversaires manqués (hier ou avant-hier).
                Utilisez {"{name}"} pour insérer le prénom.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Textarea
                value={lateMessages}
                onChange={(e) => setLateMessages(e.target.value)}
                className="min-h-[400px] font-mono text-sm"
                placeholder="Désolé du retard, bon anniversaire {name} !&#10;Avec un peu de retard, joyeux anniversaire {name} !..."
              />
              <div className="flex justify-between">
                <Button variant="outline" onClick={loadMessages}>
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Recharger
                </Button>
                <Button onClick={() => handleSave('late')} disabled={saving}>
                  {saving ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Save className="mr-2 h-4 w-4" />
                  )}
                  Sauvegarder
                </Button>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
