"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Save, Loader2, RefreshCw, AlertTriangle } from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function YamlEditor() {
  const [content, setContent] = useState("")
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const { toast } = useToast()

  useEffect(() => {
    loadYaml()
  }, [])

  const loadYaml = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/settings/yaml')
      if (!res.ok) throw new Error('Failed to load config')
      const data = await res.json()
      setContent(data.content)
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: "Impossible de charger la configuration YAML"
      })
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    setSaving(true)
    try {
      const res = await fetch('/api/settings/yaml', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content })
      })

      if (!res.ok) {
        const data = await res.json()
        throw new Error(data.detail || 'Failed to save')
      }

      toast({
        title: "Succès",
        description: "Configuration YAML sauvegardée"
      })
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Erreur de validation",
        description: error instanceof Error ? error.message : "Erreur inconnue"
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
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          Éditeur YAML Avancé
          <span className="text-xs bg-amber-500/10 text-amber-500 px-2 py-1 rounded font-normal flex items-center gap-1">
            <AlertTriangle className="h-3 w-3" />
            Attention: Pour utilisateurs avancés
          </span>
        </CardTitle>
        <CardDescription>
          Modifiez directement le fichier config.yaml. Assurez-vous de respecter la syntaxe YAML.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Textarea
          value={content}
          onChange={(e) => setContent(e.target.value)}
          className="min-h-[500px] font-mono text-sm bg-slate-950 text-slate-100 border-slate-800"
          spellCheck={false}
        />
        <div className="flex justify-between">
          <Button variant="outline" onClick={loadYaml}>
            <RefreshCw className="mr-2 h-4 w-4" />
            Recharger
          </Button>
          <Button onClick={handleSave} disabled={saving} variant="destructive">
            {saving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Sauvegarder (Force)
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}
