"use client"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Download, Github, Bug } from "lucide-react"
import { downloadDebugReport } from "@/lib/api"
import { useToast } from "@/components/ui/use-toast"
import { useState } from "react"
import { SettingsForm } from "@/components/settings/SettingsForm"

export default function SettingsPage() {
  const { toast } = useToast()
  const [downloading, setDownloading] = useState(false)

  const handleDownloadReport = async () => {
    setDownloading(true)
    try {
      const blob = await downloadDebugReport()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `debug_report_${new Date().toISOString()}.zip`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast({ title: "Téléchargement lancé", description: "Le rapport a été généré." })
    } catch (e) {
      toast({ variant: "destructive", title: "Erreur", description: "Impossible de télécharger le rapport." })
    } finally {
      setDownloading(false)
    }
  }

  const handleGithubIssue = () => {
    const params = new URLSearchParams({
      title: "[Bug] Description du problème",
      body: `**Description**\nDescribe the issue...\n\n**Technical Info**\nDashboard Version: 2.0.0\nUser Agent: ${navigator.userAgent}\n\n**Logs**\n(Attach the debug report zip here)`
    })
    window.open(`https://github.com/gaspardd78/linkedin-birthday-auto/issues/new?${params.toString()}`, '_blank')
  }

  return (
    <div className="container mx-auto py-8 space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Paramètres</h1>
        <p className="text-muted-foreground">Configuration et maintenance du système.</p>
      </div>

      <div className="grid gap-6">
        {/* Zone Debug & Support - Toujours visible en haut */}
        <Card className="border-orange-500/20 bg-orange-500/5">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-orange-500">
              <Bug className="h-5 w-5" />
              Support & Debug
            </CardTitle>
            <CardDescription>
              Outils pour diagnostiquer les problèmes et contacter le support.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col sm:flex-row gap-4">
            <Button
              variant="outline"
              className="flex-1 h-auto py-4 flex flex-col items-center gap-2 border-dashed"
              onClick={handleDownloadReport}
              disabled={downloading}
            >
              <Download className="h-6 w-6 mb-1" />
              <div className="text-center">
                <span className="font-semibold block">
                  {downloading ? "Génération..." : "Télécharger Rapport Crash"}
                </span>
                <span className="text-xs text-muted-foreground font-normal">
                  Logs, screenshots et dumps HTML (ZIP)
                </span>
              </div>
            </Button>

            <Button
              variant="secondary"
              className="flex-1 h-auto py-4 flex flex-col items-center gap-2"
              onClick={handleGithubIssue}
            >
              <Github className="h-6 w-6 mb-1" />
              <div className="text-center">
                <span className="font-semibold block">Ouvrir une Issue GitHub</span>
                <span className="text-xs text-muted-foreground font-normal">
                  Signaler un bug ou proposer une feature
                </span>
              </div>
            </Button>
          </CardContent>
        </Card>

        {/* Le formulaire gère désormais ses propres onglets (Vertical Tabs) */}
        <SettingsForm />
      </div>
    </div>
  )
}
