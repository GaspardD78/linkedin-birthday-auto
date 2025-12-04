"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Textarea } from "@/components/ui/textarea"
import { useToast } from "@/components/ui/use-toast"
import {
  FileCode,
  Save,
  RefreshCw,
  AlertTriangle,
  CheckCircle2,
  Download,
  Upload
} from "lucide-react"

export function ConfigFileEditor() {
  const [content, setContent] = useState<string>("")
  const [originalContent, setOriginalContent] = useState<string>("")
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)
  const { toast } = useToast()

  useEffect(() => {
    fetchConfigContent()
  }, [])

  useEffect(() => {
    setHasChanges(content !== originalContent)
    validateYAML(content)
  }, [content, originalContent])

  const fetchConfigContent = async () => {
    try {
      setLoading(true)
      const response = await fetch('/api/config/file')
      if (!response.ok) throw new Error('Échec du chargement du fichier')

      const data = await response.json()
      setContent(data.content)
      setOriginalContent(data.content)
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setLoading(false)
    }
  }

  const validateYAML = (yamlContent: string) => {
    try {
      // Basic YAML validation (just checking for obvious syntax errors)
      const lines = yamlContent.split('\n')
      let indentStack: number[] = [0]

      for (let i = 0; i < lines.length; i++) {
        const line = lines[i]
        if (line.trim() === '' || line.trim().startsWith('#')) continue

        const indent = line.search(/\S/)
        if (indent === -1) continue

        // Check for tabs (YAML doesn't allow tabs)
        if (line.includes('\t')) {
          setValidationError(`Ligne ${i + 1}: Les tabulations ne sont pas autorisées en YAML`)
          return false
        }

        // Check for proper indentation (must be multiples of 2)
        if (indent % 2 !== 0) {
          setValidationError(`Ligne ${i + 1}: L'indentation doit être un multiple de 2`)
          return false
        }
      }

      setValidationError(null)
      return true
    } catch (error) {
      setValidationError("Syntaxe YAML invalide")
      return false
    }
  }

  const handleSave = async () => {
    if (!validateYAML(content)) {
      toast({
        variant: "destructive",
        title: "Validation échouée",
        description: validationError || "Le fichier YAML contient des erreurs"
      })
      return
    }

    try {
      setSaving(true)
      const response = await fetch('/api/config/file', {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ content })
      })

      if (!response.ok) throw new Error('Échec de la sauvegarde')

      setOriginalContent(content)
      toast({
        title: "Sauvegarde réussie",
        description: "Le fichier config.yaml a été mis à jour"
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

  const handleReset = () => {
    setContent(originalContent)
    toast({
      title: "Modifications annulées",
      description: "Le contenu a été restauré"
    })
  }

  const handleDownload = () => {
    const blob = new Blob([content], { type: 'text/yaml' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `config-${new Date().toISOString().slice(0, 10)}.yaml`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    toast({
      title: "Téléchargement lancé",
      description: "Le fichier de configuration a été téléchargé"
    })
  }

  const handleFileUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    const reader = new FileReader()
    reader.onload = (e) => {
      const text = e.target?.result as string
      setContent(text)
      toast({
        title: "Fichier chargé",
        description: "Le contenu a été importé. N'oubliez pas de sauvegarder."
      })
    }
    reader.readAsText(file)
  }

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-6 bg-slate-700 rounded w-1/3 animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-slate-800/50 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <FileCode className="h-5 w-5 text-cyan-500" />
              Éditeur config.yaml
            </CardTitle>
            <CardDescription className="mt-2">
              Modifiez directement le fichier de configuration. Les changements seront appliqués immédiatement.
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            {hasChanges && (
              <Badge variant="outline" className="border-amber-500 text-amber-400">
                <AlertTriangle className="h-3 w-3 mr-1" />
                Non sauvegardé
              </Badge>
            )}
            {!hasChanges && validationError === null && (
              <Badge variant="outline" className="border-emerald-500 text-emerald-400">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Valide
              </Badge>
            )}
            {validationError && (
              <Badge variant="outline" className="border-red-500 text-red-400">
                <AlertTriangle className="h-3 w-3 mr-1" />
                Erreur
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* Validation Error */}
        {validationError && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/30">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-red-400 mb-1">Erreur de validation</h4>
              <p className="text-xs text-red-200/80">{validationError}</p>
            </div>
          </div>
        )}

        {/* Editor */}
        <div className="relative">
          <Textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="font-mono text-xs bg-slate-950 border-slate-700 min-h-[500px] resize-y"
            placeholder="Configuration YAML..."
            spellCheck={false}
          />
          <div className="absolute bottom-2 right-2 text-xs text-slate-500 font-mono">
            {content.split('\n').length} lignes
          </div>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between gap-4 pt-4 border-t border-slate-800">
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleDownload}
              className="gap-2 border-slate-700 hover:bg-slate-800"
            >
              <Download className="h-4 w-4" />
              Télécharger
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => document.getElementById('file-upload')?.click()}
              className="gap-2 border-slate-700 hover:bg-slate-800"
            >
              <Upload className="h-4 w-4" />
              Importer
            </Button>
            <input
              id="file-upload"
              type="file"
              accept=".yaml,.yml"
              onChange={handleFileUpload}
              className="hidden"
            />
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={!hasChanges}
              className="gap-2 border-slate-700 hover:bg-slate-800"
            >
              <RefreshCw className="h-4 w-4" />
              Annuler
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleSave}
              disabled={!hasChanges || validationError !== null || saving}
              className="gap-2 bg-cyan-600 hover:bg-cyan-700"
            >
              {saving ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" />
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
        </div>

        {/* Help */}
        <div className="text-xs text-slate-500 pt-2 border-t border-slate-800">
          <p><strong>💡 Conseils :</strong></p>
          <ul className="list-disc list-inside mt-1 space-y-1">
            <li>Utilisez 2 espaces pour l'indentation (pas de tabulations)</li>
            <li>Les lignes commençant par # sont des commentaires</li>
            <li>Sauvegardez régulièrement vos modifications</li>
            <li>Téléchargez une copie de sauvegarde avant les modifications importantes</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  )
}
