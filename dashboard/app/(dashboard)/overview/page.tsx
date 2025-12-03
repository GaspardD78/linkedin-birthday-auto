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
  Eye,
  Settings as SettingsIcon,
  Cookie
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { getBotStatusDetailed, BotStatusDetailed } from "@/lib/api"
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
  visits: number
  errors: number
  status: 'success' | 'error' | 'none'
  type: 'birthday' | 'visitor' | null
}

interface BotConfig {
  max_per_day: number
  schedule_time: string
  auto_run_enabled: boolean
  mode?: string
}

export default function OverviewPage() {
  const [botStatus, setBotStatus] = useState<BotStatusDetailed | null>(null)
  const [lastRunBirthday, setLastRunBirthday] = useState<LastRunInfo>({
    date: null, messages_sent: 0, messages_ignored: 0, visits: 0, errors: 0, status: 'none', type: 'birthday'
  })
  const [lastRunVisitor, setLastRunVisitor] = useState<LastRunInfo>({
    date: null, messages_sent: 0, messages_ignored: 0, visits: 0, errors: 0, status: 'none', type: 'visitor'
  })
  const [birthdayConfig, setBirthdayConfig] = useState<BotConfig | null>(null)
  const [visitorConfig, setVisitorConfig] = useState<BotConfig | null>(null)
  const [cookiesValid, setCookiesValid] = useState<boolean>(true)
  const [cookiesLastUpdated, setCookiesLastUpdated] = useState<string | null>(null)
  const [weekSummary, setWeekSummary] = useState<ActivitySummary[]>([])
  const [recentLogs, setRecentLogs] = useState<string[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [autoRunBirthdayEnabled, setAutoRunBirthdayEnabled] = useState(false)
  const [autoRunVisitorEnabled, setAutoRunVisitorEnabled] = useState(false)
  const { toast } = useToast()

  // Fetch all data
  const fetchData = async () => {
    try {
      // Get bot status
      const status = await getBotStatusDetailed()
      setBotStatus(status)

      // Get config for both bots
      try {
        const configRes = await fetch('/api/settings/yaml')
        if (configRes.ok) {
          const configData = await configRes.json()
          const yaml = await import('js-yaml')
          const config: any = yaml.load(configData.content)

          // Birthday Bot Config
          setBirthdayConfig({
            max_per_day: config.messaging_limits?.daily_message_limit || 50,
            schedule_time: `${String(config.scheduling?.daily_start_hour || 7).padStart(2, '0')}:30`,
            auto_run_enabled: false, // TODO: Implement persistence
            mode: config.bot_mode || 'standard'
          })

          // Visitor Bot Config
          setVisitorConfig({
            max_per_day: config.visitor?.limits?.profiles_per_run || 15,
            schedule_time: `${String(config.scheduling?.daily_start_hour || 14).padStart(2, '0')}:00`,
            auto_run_enabled: false, // TODO: Implement persistence
            mode: 'visit'
          })

          // Cookies status (check auth_state)
          setCookiesValid(true) // TODO: Get from API
          setCookiesLastUpdated(new Date().toISOString())
        }
      } catch (err) {
        console.error('Failed to load config:', err)
      }

      // Get last 7 days activity
      const historyRes = await fetch('/api/history?days=7')
      if (historyRes.ok) {
        const historyData = await historyRes.json()
        setWeekSummary(historyData.activity || [])

        // Calculate last run for each bot from activity
        if (historyData.activity && historyData.activity.length > 0) {
          const latestDay = historyData.activity[historyData.activity.length - 1]

          // Birthday Bot last run
          if (latestDay.messages > 0) {
            setLastRunBirthday({
              date: latestDay.date,
              messages_sent: latestDay.messages || 0,
              messages_ignored: 0, // TODO: Get from API
              visits: 0,
              errors: latestDay.errors || 0,
              status: latestDay.errors > 0 ? 'error' : 'success',
              type: 'birthday'
            })
          }

          // Visitor Bot last run
          if (latestDay.visits > 0) {
            setLastRunVisitor({
              date: latestDay.date,
              messages_sent: 0,
              messages_ignored: 0,
              visits: latestDay.visits || 0,
              errors: 0,
              status: 'success',
              type: 'visitor'
            })
          }
        }
      }

      // Get recent logs
      const logsRes = await fetch('/api/logs?limit=30')
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

  // Check if there's a birthday job running
  const isBirthdayJobRunning = botStatus && botStatus.active_jobs.some(j => j.type === 'birthday')
  const birthdayJob = botStatus?.active_jobs.find(j => j.type === 'birthday')

  // Check if there's a visitor job running
  const isVisitorJobRunning = botStatus && botStatus.active_jobs.some(j => j.type === 'visit')
  const visitorJob = botStatus?.active_jobs.find(j => j.type === 'visit')

  // Global status
  const isAnyJobRunning = isBirthdayJobRunning || isVisitorJobRunning

  // Handle start birthday bot
  const handleStartBirthdayBot = async () => {
    if (isVisitorJobRunning) {
      const confirm = window.confirm("⚠️ Le bot Visiteur est en cours d'exécution. Voulez-vous lancer le bot d'Anniversaire en même temps ?")
      if (!confirm) return
    }

    setLoading('start-birthday')
    try {
      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          action: 'start',
          job_type: 'birthday',
          dry_run: false,
          process_late: false
        })
      })

      if (!response.ok) throw new Error('Failed to start birthday bot')

      toast({ title: "Bot Anniversaire démarré", description: "Le bot d'anniversaire a été lancé avec succès." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle start visitor bot
  const handleStartVisitorBot = async () => {
    if (isBirthdayJobRunning) {
      const confirm = window.confirm("⚠️ Le bot d'Anniversaire est en cours d'exécution. Voulez-vous lancer le bot Visiteur en même temps ?")
      if (!confirm) return
    }

    setLoading('start-visitor')
    try {
      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          action: 'start',
          job_type: 'visit',
          dry_run: false,
          limit: 15
        })
      })

      if (!response.ok) throw new Error('Failed to start visitor bot')

      toast({ title: "Bot Visiteur démarré", description: "Le bot visiteur a été lancé avec succès." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle stop birthday job
  const handleStopBirthdayJob = async () => {
    if (!birthdayJob) return

    setLoading('stop-birthday')
    try {
      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          action: 'stop',
          job_id: birthdayJob.id
        })
      })

      if (!response.ok) throw new Error('Failed to stop birthday bot')

      toast({ title: "Arrêt demandé", description: "La demande d'arrêt a été envoyée au bot d'Anniversaire." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle stop visitor job
  const handleStopVisitorJob = async () => {
    if (!visitorJob) return

    setLoading('stop-visitor')
    try {
      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          action: 'stop',
          job_id: visitorJob.id
        })
      })

      if (!response.ok) throw new Error('Failed to stop visitor bot')

      toast({ title: "Arrêt demandé", description: "La demande d'arrêt a été envoyée au bot Visiteur." })
      await fetchData()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  // Handle toggle auto-run (Birthday)
  const handleToggleAutoRunBirthday = () => {
    setAutoRunBirthdayEnabled(!autoRunBirthdayEnabled)
    toast({
      title: autoRunBirthdayEnabled ? "Auto-run Anniversaire désactivé" : "Auto-run Anniversaire activé",
      description: autoRunBirthdayEnabled
        ? "Les runs automatiques du bot d'Anniversaire sont désactivés."
        : "Les runs automatiques du bot d'Anniversaire sont activés."
    })
    // TODO: Persist to API
  }

  // Handle toggle auto-run (Visitor)
  const handleToggleAutoRunVisitor = () => {
    setAutoRunVisitorEnabled(!autoRunVisitorEnabled)
    toast({
      title: autoRunVisitorEnabled ? "Auto-run Visiteur désactivé" : "Auto-run Visiteur activé",
      description: autoRunVisitorEnabled
        ? "Les runs automatiques du bot Visiteur sont désactivés."
        : "Les runs automatiques du bot Visiteur sont activés."
    })
    // TODO: Persist to API
  }

  // Calculate week totals
  const weekTotals = weekSummary.reduce((acc, day) => ({
    messages: acc.messages + (day.messages || 0),
    visits: acc.visits + (day.visits || 0),
    errors: acc.errors + (day.errors || 0)
  }), { messages: 0, visits: 0, errors: 0 })

  // Syntax highlighting for logs
  const formatLogLine = (log: string) => {
    try {
      const parsed = JSON.parse(log)
      const level = (parsed.level || 'INFO').toUpperCase()
      const message = parsed.event || parsed.message || log
      const timestamp = parsed.timestamp || parsed.event_time || ''

      let levelColor = 'text-slate-400'
      let bgColor = 'hover:bg-slate-800/50'

      if (level.includes('ERROR') || level.includes('CRITICAL')) {
        levelColor = 'text-red-400'
        bgColor = 'hover:bg-red-900/20'
      } else if (level.includes('WARNING') || level.includes('WARN')) {
        levelColor = 'text-amber-400'
        bgColor = 'hover:bg-amber-900/20'
      } else if (level.includes('SUCCESS')) {
        levelColor = 'text-green-400'
        bgColor = 'hover:bg-green-900/20'
      } else if (level.includes('INFO')) {
        levelColor = 'text-blue-400'
        bgColor = 'hover:bg-blue-900/20'
      } else if (level.includes('DEBUG')) {
        levelColor = 'text-purple-400'
        bgColor = 'hover:bg-purple-900/20'
      }

      return (
        <div className={`px-2 py-1 rounded transition-colors ${bgColor}`}>
          <span className="text-slate-500 text-[10px]">{timestamp.slice(11, 19)}</span>
          <span className={`ml-2 font-semibold ${levelColor}`}>[{level}]</span>
          <span className="ml-2 text-slate-300">{message}</span>
        </div>
      )
    } catch {
      // Fallback for non-JSON logs
      const levelMatch = log.match(/\b(DEBUG|INFO|WARNING|ERROR|CRITICAL|SUCCESS)\b/i)
      const level = levelMatch ? levelMatch[1].toUpperCase() : 'INFO'

      let levelColor = 'text-slate-400'
      if (level.includes('ERROR')) levelColor = 'text-red-400'
      else if (level.includes('WARNING')) levelColor = 'text-amber-400'
      else if (level.includes('SUCCESS')) levelColor = 'text-green-400'

      return (
        <div className={`px-2 py-1 rounded transition-colors hover:bg-slate-800/50 ${levelColor}`}>
          {log}
        </div>
      )
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 lg:p-6">
      <div className="max-w-7xl mx-auto space-y-6">

        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-white">Vue d'ensemble</h1>
            <p className="text-slate-400 mt-1">Pilotage et suivi de l'activité des bots</p>
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

        {/* Global System Status */}
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Activity className="h-5 w-5 text-blue-500" />
              Statut Global du Système
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-3">
                <div className="flex items-center gap-4">
                  {isAnyJobRunning ? (
                    <>
                      <div className="h-12 w-12 rounded-full bg-green-500/20 flex items-center justify-center">
                        <Activity className="h-6 w-6 text-green-500 animate-pulse" />
                      </div>
                      <div>
                        <p className="text-lg font-semibold text-white">Actif</p>
                        <p className="text-sm text-slate-400">
                          {isBirthdayJobRunning && isVisitorJobRunning
                            ? "Anniversaire + Visiteur en cours"
                            : isBirthdayJobRunning
                            ? "Bot d'Anniversaire en cours"
                            : "Bot Visiteur en cours"}
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
                        <p className="text-sm text-slate-400">Aucun bot en exécution</p>
                      </div>
                    </>
                  )}
                </div>

                <div className="space-y-1 text-sm pt-2 border-t border-slate-800">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dernier run Anniversaire:</span>
                    <span className="text-slate-200 font-mono">
                      {lastRunBirthday.date
                        ? new Date(lastRunBirthday.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                        : "Aucun"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Dernier run Visiteur:</span>
                    <span className="text-slate-200 font-mono">
                      {lastRunVisitor.date
                        ? new Date(lastRunVisitor.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
                        : "Aucun"}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex flex-col justify-center space-y-2 p-4 bg-slate-800/50 rounded-lg border border-slate-700">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Cookie className="h-4 w-4 text-cyan-400" />
                    <span className="text-sm font-semibold text-slate-200">Cookies LinkedIn</span>
                  </div>
                  <Badge variant={cookiesValid ? "default" : "destructive"} className={cookiesValid ? "bg-green-600 hover:bg-green-700" : ""}>
                    {cookiesValid ? "✅ Valides" : "⚠️ Expirés"}
                  </Badge>
                </div>
                <p className="text-xs text-slate-400">
                  Dernière mise à jour: {cookiesLastUpdated
                    ? new Date(cookiesLastUpdated).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
                    : "Inconnue"}
                </p>
                {!cookiesValid && (
                  <Link href="/settings">
                    <Button size="sm" variant="outline" className="w-full text-xs mt-2">
                      Mettre à jour
                    </Button>
                  </Link>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Bot Launchers - 2 Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">

          {/* Birthday Bot Launcher */}
          <Card className="bg-gradient-to-br from-pink-900/20 to-slate-900 border-pink-700/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-pink-400">
                🎂 Bot d'Anniversaire
              </CardTitle>
              <CardDescription>Envoi automatique de messages d'anniversaire</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">

              {/* Configuration Active */}
              <div className="space-y-2 p-3 bg-slate-950/50 rounded-lg border border-slate-800">
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Configuration Actuelle</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Mode:</span>
                    <Link href="/settings?tab=birthday">
                      <span className="text-pink-400 hover:underline cursor-pointer">{birthdayConfig?.mode === 'standard' ? 'Standard' : 'Illimité'} ⚙️</span>
                    </Link>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Max messages/jour:</span>
                    <Link href="/settings?tab=birthday">
                      <span className="text-slate-200 hover:underline cursor-pointer">{birthdayConfig?.max_per_day || 50} ⚙️</span>
                    </Link>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Horaire:</span>
                    <Link href="/settings?tab=global">
                      <span className="text-slate-200 hover:underline cursor-pointer">{birthdayConfig?.schedule_time || "07:30"} (L-V) ⚙️</span>
                    </Link>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={handleStartBirthdayBot}
                    disabled={!!loading || isBirthdayJobRunning}
                    className="bg-green-600 hover:bg-green-700 disabled:bg-slate-700"
                  >
                    {loading === 'start-birthday' ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    Lancer
                  </Button>

                  <Button
                    onClick={handleToggleAutoRunBirthday}
                    disabled={!!loading}
                    variant="outline"
                    className={autoRunBirthdayEnabled ? "border-green-600 text-green-400" : ""}
                  >
                    {autoRunBirthdayEnabled ? (
                      <><CheckCircle2 className="h-4 w-4 mr-2" />Auto ON</>
                    ) : (
                      <><Pause className="h-4 w-4 mr-2" />Auto OFF</>
                    )}
                  </Button>
                </div>

                <Button
                  onClick={handleStopBirthdayJob}
                  disabled={!isBirthdayJobRunning || loading === 'stop-birthday'}
                  variant="destructive"
                  className="w-full"
                >
                  {loading === 'stop-birthday' ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="h-4 w-4 mr-2 fill-current" />
                  )}
                  Arrêter
                </Button>
              </div>

              {/* Status */}
              <div className="pt-2 border-t border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400">📌 Statut:</span>
                  <Badge variant={isBirthdayJobRunning ? "default" : "secondary"} className={isBirthdayJobRunning ? "bg-green-600" : ""}>
                    {isBirthdayJobRunning ? "En cours" : "Idle"}
                  </Badge>
                </div>
                {lastRunBirthday.date && (
                  <p className="text-xs text-slate-400 mt-1">
                    Dernier: {new Date(lastRunBirthday.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    {" – "}
                    <span className="text-green-400">{lastRunBirthday.messages_sent} msg</span>
                    {lastRunBirthday.errors > 0 && (
                      <span className="text-red-400"> / {lastRunBirthday.errors} err</span>
                    )}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Visitor Bot Launcher */}
          <Card className="bg-gradient-to-br from-emerald-900/20 to-slate-900 border-emerald-700/40">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-emerald-400">
                👁️ Bot Visiteur
              </CardTitle>
              <CardDescription>Visite automatique de profils LinkedIn</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">

              {/* Configuration Active */}
              <div className="space-y-2 p-3 bg-slate-950/50 rounded-lg border border-slate-800">
                <h4 className="text-xs font-semibold text-slate-400 uppercase">Configuration Actuelle</h4>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-400">Mode:</span>
                    <Link href="/settings?tab=visitor">
                      <span className="text-emerald-400 hover:underline cursor-pointer">Visite Simple ⚙️</span>
                    </Link>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Max visites/jour:</span>
                    <Link href="/settings?tab=visitor">
                      <span className="text-slate-200 hover:underline cursor-pointer">{visitorConfig?.max_per_day || 15} ⚙️</span>
                    </Link>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-400">Horaire:</span>
                    <Link href="/settings?tab=global">
                      <span className="text-slate-200 hover:underline cursor-pointer">{visitorConfig?.schedule_time || "14:00"} (L-V) ⚙️</span>
                    </Link>
                  </div>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <Button
                    onClick={handleStartVisitorBot}
                    disabled={!!loading || isVisitorJobRunning}
                    className="bg-green-600 hover:bg-green-700 disabled:bg-slate-700"
                  >
                    {loading === 'start-visitor' ? (
                      <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Play className="h-4 w-4 mr-2" />
                    )}
                    Lancer
                  </Button>

                  <Button
                    onClick={handleToggleAutoRunVisitor}
                    disabled={!!loading}
                    variant="outline"
                    className={autoRunVisitorEnabled ? "border-green-600 text-green-400" : ""}
                  >
                    {autoRunVisitorEnabled ? (
                      <><CheckCircle2 className="h-4 w-4 mr-2" />Auto ON</>
                    ) : (
                      <><Pause className="h-4 w-4 mr-2" />Auto OFF</>
                    )}
                  </Button>
                </div>

                <Button
                  onClick={handleStopVisitorJob}
                  disabled={!isVisitorJobRunning || loading === 'stop-visitor'}
                  variant="destructive"
                  className="w-full"
                >
                  {loading === 'stop-visitor' ? (
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Square className="h-4 w-4 mr-2 fill-current" />
                  )}
                  Arrêter
                </Button>
              </div>

              {/* Status */}
              <div className="pt-2 border-t border-slate-800">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-slate-400">📌 Statut:</span>
                  <Badge variant={isVisitorJobRunning ? "default" : "secondary"} className={isVisitorJobRunning ? "bg-green-600" : ""}>
                    {isVisitorJobRunning ? "En cours" : "Idle"}
                  </Badge>
                </div>
                {lastRunVisitor.date && (
                  <p className="text-xs text-slate-400 mt-1">
                    Dernier: {new Date(lastRunVisitor.date).toLocaleDateString('fr-FR', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                    {" – "}
                    <span className="text-emerald-400">{lastRunVisitor.visits} visits</span>
                  </p>
                )}
              </div>
            </CardContent>
          </Card>

        </div>

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

        {/* Recent Logs with Syntax Highlighting */}
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
                  <div key={idx}>
                    {formatLogLine(log)}
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
