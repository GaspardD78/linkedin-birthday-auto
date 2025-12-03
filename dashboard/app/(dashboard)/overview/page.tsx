"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Activity,
  Play,
  Pause,
  Square,
  Calendar,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  Clock,
  MessageSquare,
  UserX,
  AlertTriangle,
  RefreshCw,
  Eye
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { getBotStatusDetailed, startBot, stopBot, BotStatusDetailed } from "@/lib/api"
import Link from "next/link"

interface ActivitySummary {
  date: string
  messages: number
  late_messages: number
  visits: number
  errors: number
}

interface LastRunInfo {
  date: string | null
  messages_sent: number
  messages_ignored: number
  errors: number
  status: 'success' | 'error' | 'none'
}

export default function OverviewPage() {
  const [botStatus, setBotStatus] = useState<BotStatusDetailed | null>(null)
  const [lastRun, setLastRun] = useState<LastRunInfo>({
    date: null,
    messages_sent: 0,
    messages_ignored: 0,
    errors: 0,
    status: 'none'
  })
  const [weekSummary, setWeekSummary] = useState<ActivitySummary[]>([])
  const [recentLogs, setRecentLogs] = useState<string[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [autoRunEnabled, setAutoRunEnabled] = useState(false) // TODO: Implement actual persistence
  const { toast } = useToast()

  // Fetch all data
  const fetchData = async () => {
    try {
      // Get bot status
      const status = await getBotStatusDetailed()
      setBotStatus(status)

      // Get last 7 days activity
      const historyRes = await fetch('/api/history?days=7')
      if (historyRes.ok) {
        const historyData = await historyRes.json()
        setWeekSummary(historyData.activity || [])

        // Calculate last run from activity
        if (historyData.activity && historyData.activity.length > 0) {
          const latestDay = historyData.activity[historyData.activity.length - 1]
          if (latestDay.messages > 0 || latestDay.visits > 0) {
            setLastRun({
              date: latestDay.date,
              messages_sent: latestDay.messages || 0,
              messages_ignored: 0, // TODO: Get from API
              errors: latestDay.errors || 0,
              status: latestDay.errors > 0 ? 'error' : 'success'
            })
          }
        }
      }

      // Get recent logs
      const logsRes = await fetch('/api/logs?limit=20')
      if (logsRes.ok) {
        const logsData = await logsRes.json()
        setRecentLogs(logsData.logs || [])
      }
    } catch (error) {
      console.error('Failed to fetch overview data:', error)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  // Check if there's a job running
  const isJobRunning = botStatus && botStatus.active_jobs.length > 0
  const currentJob = isJobRunning ? botStatus.active_jobs[0] : null

  // Handle start bot
  const handleStartBot = async () => {
    setLoading('start')
    try {
      await startBot({ dryRun: false, processLate: false })
      toast({ title: "Bot démarré", description: "Le bot d'anniversaire a été lancé." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle stop current job
  const handleStopJob = async () => {
    if (!currentJob) return

    setLoading('stop')
    try {
      await stopBot(undefined, currentJob.id)
      toast({ title: "Arrêt demandé", description: "La demande d'arrêt a été envoyée au bot." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle toggle auto-run
  const handleToggleAutoRun = () => {
    setAutoRunEnabled(!autoRunEnabled)
    toast({
      title: autoRunEnabled ? "Auto-run désactivé" : "Auto-run activé",
      description: autoRunEnabled
        ? "Les runs automatiques sont maintenant désactivés."
        : "Les runs automatiques sont maintenant activés."
    })
  }

  // Calculate week totals
  const weekTotals = weekSummary.reduce((acc, day) => ({
    messages: acc.messages + (day.messages || 0),
    visits: acc.visits + (day.visits || 0),
    errors: acc.errors + (day.errors || 0)
  }), { messages: 0, visits: 0, errors: 0 })

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 lg:p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Vue d'ensemble</h1>
            <p className="text-slate-400 mt-1">Pilotage et suivi de l'activité du bot</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={fetchData}
            className="gap-2"
          >
            <RefreshCw className="h-4 w-4" />
            Actualiser
          </Button>
        </div>

        {/* Status Card */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Statut du Bot
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                {isJobRunning ? (
                  <>
                    <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                      <Activity className="h-6 w-6 text-green-500 animate-pulse" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-white">Actif</p>
                      <p className="text-sm text-slate-400">
                        Job en cours: {currentJob?.type} ({currentJob?.id.slice(0, 8)}...)
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="h-12 w-12 rounded-full bg-slate-700/50 flex items-center justify-center">
                      <Pause className="h-6 w-6 text-slate-400" />
                    </div>
                    <div>
                      <p className="text-lg font-semibold text-white">Arrêté</p>
                      <p className="text-sm text-slate-400">Aucun job en cours d'exécution</p>
                    </div>
                  </>
                )}
              </div>
              <Badge variant={isJobRunning ? "default" : "secondary"} className={isJobRunning ? "bg-green-600 hover:bg-green-700" : ""}>
                {isJobRunning ? "Running" : "Idle"}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Last Run & Next Run */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">

          {/* Last Run */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Calendar className="h-4 w-4 text-blue-400" />
                Dernier Run
              </CardTitle>
            </CardHeader>
            <CardContent>
              {lastRun.date ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Date</span>
                    <span className="text-sm font-mono text-slate-200">
                      {new Date(lastRun.date).toLocaleString('fr-FR')}
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Messages envoyés</span>
                    <Badge variant="outline" className="text-green-400 border-green-700">
                      <MessageSquare className="h-3 w-3 mr-1" />
                      {lastRun.messages_sent}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Messages ignorés</span>
                    <Badge variant="outline" className="text-slate-400 border-slate-700">
                      <UserX className="h-3 w-3 mr-1" />
                      {lastRun.messages_ignored}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-400">Erreurs</span>
                    <Badge variant="outline" className={lastRun.errors > 0 ? "text-red-400 border-red-700" : "text-slate-400 border-slate-700"}>
                      <AlertTriangle className="h-3 w-3 mr-1" />
                      {lastRun.errors}
                    </Badge>
                  </div>
                  {lastRun.status === 'success' ? (
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                      <CheckCircle2 className="h-4 w-4 text-green-500" />
                      <span className="text-sm text-green-400">Run terminé avec succès</span>
                    </div>
                  ) : lastRun.status === 'error' ? (
                    <div className="flex items-center gap-2 pt-2 border-t border-slate-800">
                      <AlertCircle className="h-4 w-4 text-red-500" />
                      <span className="text-sm text-red-400">Run terminé avec erreurs</span>
                    </div>
                  ) : null}
                </div>
              ) : (
                <div className="text-center py-6">
                  <Clock className="h-8 w-8 text-slate-600 mx-auto mb-2" />
                  <p className="text-sm text-slate-500">Aucun run récent</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Next Run */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4 text-amber-400" />
                Prochain Run Planifié
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-center py-6">
                <AlertCircle className="h-8 w-8 text-amber-500 mx-auto mb-2" />
                <p className="text-sm text-amber-400 font-semibold mb-1">Mode Manuel Uniquement</p>
                <p className="text-xs text-slate-500">Aucun run automatique planifié</p>
                <p className="text-xs text-slate-500 mt-2">
                  {autoRunEnabled ? "Auto-run activé (à implémenter)" : "Auto-run désactivé"}
                </p>
              </div>
            </CardContent>
          </Card>

        </div>

        {/* Quick Actions */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Actions Rapides
            </CardTitle>
            <CardDescription>Contrôlez le bot directement depuis cette page</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">

              {/* Start Bot */}
              <Button
                onClick={handleStartBot}
                disabled={!!loading || isJobRunning}
                className="h-auto py-4 flex-col gap-2 bg-green-600 hover:bg-green-700"
              >
                {loading === 'start' ? (
                  <RefreshCw className="h-5 w-5 animate-spin" />
                ) : (
                  <Play className="h-5 w-5" />
                )}
                <span>Lancer un run maintenant</span>
              </Button>

              {/* Toggle Auto-Run */}
              <Button
                onClick={handleToggleAutoRun}
                disabled={!!loading}
                variant="outline"
                className="h-auto py-4 flex-col gap-2"
              >
                {autoRunEnabled ? (
                  <Pause className="h-5 w-5" />
                ) : (
                  <Play className="h-5 w-5" />
                )}
                <span>
                  {autoRunEnabled ? "Mettre en pause l'auto-run" : "Réactiver l'auto-run"}
                </span>
              </Button>

              {/* Stop Current Job */}
              <Button
                onClick={handleStopJob}
                disabled={!isJobRunning || loading === 'stop'}
                variant="destructive"
                className="h-auto py-4 flex-col gap-2"
              >
                {loading === 'stop' ? (
                  <RefreshCw className="h-5 w-5 animate-spin" />
                ) : (
                  <Square className="h-5 w-5 fill-current" />
                )}
                <span>Arrêter le run en cours</span>
              </Button>

            </div>

            {!isJobRunning && (
              <div className="mt-4 text-center text-xs text-slate-500">
                Le bouton "Arrêter le run en cours" n'est disponible que lorsqu'un job est actif.
              </div>
            )}
          </CardContent>
        </Card>

        {/* 7 Days Summary */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-green-500" />
              Résumé des 7 Derniers Jours
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
              <div className="bg-gradient-to-br from-blue-900/30 to-blue-800/20 border border-blue-700/40 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <MessageSquare className="h-4 w-4 text-blue-400" />
                  <span className="text-xs text-slate-400 uppercase font-semibold">Messages</span>
                </div>
                <div className="text-3xl font-bold text-blue-400">{weekTotals.messages}</div>
                <div className="text-xs text-slate-500 mt-1">envoyés cette semaine</div>
              </div>

              <div className="bg-gradient-to-br from-green-900/30 to-green-800/20 border border-green-700/40 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="h-4 w-4 text-green-400" />
                  <span className="text-xs text-slate-400 uppercase font-semibold">Visites</span>
                </div>
                <div className="text-3xl font-bold text-green-400">{weekTotals.visits}</div>
                <div className="text-xs text-slate-500 mt-1">profils visités</div>
              </div>

              <div className="bg-gradient-to-br from-red-900/30 to-red-800/20 border border-red-700/40 rounded-lg p-4">
                <div className="flex items-center gap-2 mb-2">
                  <AlertTriangle className="h-4 w-4 text-red-400" />
                  <span className="text-xs text-slate-400 uppercase font-semibold">Erreurs</span>
                </div>
                <div className="text-3xl font-bold text-red-400">{weekTotals.errors}</div>
                <div className="text-xs text-slate-500 mt-1">erreurs détectées</div>
              </div>
            </div>

            {/* Daily breakdown */}
            <div className="space-y-2">
              {weekSummary.slice(-7).reverse().map((day, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg border border-slate-700/50">
                  <span className="text-sm text-slate-300 font-mono">
                    {new Date(day.date).toLocaleDateString('fr-FR', { weekday: 'short', month: 'short', day: 'numeric' })}
                  </span>
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-1 text-xs text-blue-400">
                      <MessageSquare className="h-3 w-3" />
                      <span>{day.messages || 0}</span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-green-400">
                      <Eye className="h-3 w-3" />
                      <span>{day.visits || 0}</span>
                    </div>
                    {day.errors > 0 && (
                      <div className="flex items-center gap-1 text-xs text-red-400">
                        <AlertTriangle className="h-3 w-3" />
                        <span>{day.errors}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>

            {weekSummary.length === 0 && (
              <div className="text-center py-8 text-slate-500">
                <TrendingUp className="h-8 w-8 mx-auto mb-2 opacity-50" />
                <p className="text-sm">Aucune activité enregistrée</p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Logs */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-purple-500" />
              Logs Récents
            </CardTitle>
            <Link href="/logs">
              <Button variant="outline" size="sm" className="gap-2">
                <Eye className="h-4 w-4" />
                Voir plus
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs space-y-1 max-h-96 overflow-y-auto border border-slate-800">
              {recentLogs.length > 0 ? (
                recentLogs.map((log, idx) => (
                  <div key={idx} className="text-slate-400 hover:bg-slate-800/50 px-2 py-1 rounded transition-colors">
                    {log}
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-600">
                  <p>Aucun log disponible</p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>

      </div>
    </div>
  )
}
