"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Progress } from "@/components/ui/progress"
import Link from "next/link"
import {
  getBotStatusDetailed,
  startBot,
  startVisitorBot,
  stopBot,
  BotStatusDetailed
} from "@/lib/api"
import {
  Play,
  Square,
  Activity,
  Gift,
  Users,
  Infinity as InfinityIcon,
  AlertTriangle,
  Settings as SettingsIcon,
  Clock
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function BotControlPanel() {
  const [status, setStatus] = useState<BotStatusDetailed | null>(null)
  const [loading, setLoading] = useState<string | null>(null)
  const [dryRun, setDryRun] = useState<boolean>(true) // Default to dry-run for safety
  const { toast } = useToast()

  const refreshStatus = async () => {
    try {
      const data = await getBotStatusDetailed()
      setStatus(data)
    } catch (error) {
      console.error("Failed to fetch status", error)
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  // Helper to check if a specific type is running
  const isRunning = (type: string) => {
    return status?.active_jobs.some(job => job.type === type)
  }

  const getJobId = (type: string) => {
    return status?.active_jobs.find(job => job.type === type)?.id
  }

  const getJobProgress = (type: string) => {
    const job = status?.active_jobs.find(job => job.type === type)
    if (!job) return null
    // Simulated progress - you can enhance this with real data from job
    return {
      current: job.progress || 0,
      total: job.total || 100,
      percentage: job.progress ? (job.progress / (job.total || 100)) * 100 : 0
    }
  }

  const handleStart = async (type: 'birthday' | 'visitor' | 'unlimited') => {
    setLoading(type)
    try {
      if (type === 'birthday') {
        await startBot({ dryRun, processLate: false })
      } else if (type === 'unlimited') {
        await startBot({ dryRun, processLate: true })
      } else if (type === 'visitor') {
        await startVisitorBot({ dryRun })
      }

      const mode = dryRun ? "test (dry-run)" : "production"
      toast({
        title: "Bot démarré",
        description: `Le bot ${type} a été lancé en mode ${mode}.`,
      })
      await refreshStatus()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  const handleStop = async (type: string, jobId?: string) => {
    setLoading(`stop-${type}`)
    try {
      await stopBot(type, jobId)
      toast({ title: "Bot arrêté", description: `Arrêt du bot ${type} demandé.` })
      await refreshStatus()
    } catch (error: any) {
      toast({ variant: "destructive", title: "Erreur", description: error.message })
    } finally {
      setLoading(null)
    }
  }

  const BotCard = ({
    type,
    title,
    icon: Icon,
    description,
    color,
    settingsLink
  }: {
    type: 'birthday' | 'visitor' | 'unlimited'
    title: string
    icon: any
    description: string
    color: string
    settingsLink: string
  }) => {
    const running = isRunning(type === 'unlimited' ? 'birthday' : type)
    const activeJobId = getJobId(type === 'unlimited' ? 'birthday' : type)
    const stopKey = `stop-${type}`
    const progress = getJobProgress(type === 'unlimited' ? 'birthday' : type)

    return (
      <Card className={`bg-gradient-to-br from-${color}-900/20 to-slate-900 border-${color}-700/40 transition-all duration-300 hover:shadow-lg hover:shadow-${color}-500/10`}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className={`p-2 rounded-full ${running ? `bg-${color}-500/20` : 'bg-slate-800/50'}`}>
                <Icon className={`h-5 w-5 ${running ? `text-${color}-400` : 'text-slate-400'}`} />
              </div>
              <div>
                <CardTitle className={`text-lg ${running ? `text-${color}-400` : 'text-slate-200'}`}>
                  {title}
                </CardTitle>
                <CardDescription className="text-xs mt-1">{description}</CardDescription>
              </div>
            </div>
            <Badge variant={running ? "default" : "secondary"} className={running ? `bg-emerald-600 hover:bg-emerald-700 animate-pulse` : ""}>
              {running ? "En cours" : "Idle"}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">

          {/* Progress Bar (if running) */}
          {running && progress && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400">
                <span className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  Progression
                </span>
                <span className="font-mono">{progress.current} / {progress.total}</span>
              </div>
              <Progress value={progress.percentage} className="h-2" />
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {running ? (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => handleStop(type === 'unlimited' ? 'birthday' : type, activeJobId)}
                disabled={loading === stopKey}
                className="flex-1"
              >
                {loading === stopKey ? (
                  <span className="animate-spin mr-2">⏳</span>
                ) : (
                  <Square className="h-4 w-4 mr-2 fill-current" />
                )}
                Arrêter
              </Button>
            ) : (
              <>
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handleStart(type)}
                  disabled={!!loading || (status?.worker_status === 'working')}
                  className={`flex-1 bg-${color}-600 hover:bg-${color}-700`}
                >
                  {loading === type ? (
                    <span className="animate-spin mr-2">⏳</span>
                  ) : (
                    <Play className="h-4 w-4 mr-2 fill-current" />
                  )}
                  Démarrer
                </Button>
                <Link href={settingsLink}>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-slate-700 hover:bg-slate-800"
                  >
                    <SettingsIcon className="h-4 w-4" />
                  </Button>
                </Link>
              </>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-slate-200">
          <Activity className="h-5 w-5 text-blue-500" />
          Pilotage des Bots
        </CardTitle>
        <CardDescription>
          Contrôle centralisé de tous les processus d'automatisation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">

        {/* Dry Run Toggle */}
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className={`h-5 w-5 ${dryRun ? 'text-amber-500' : 'text-red-500'}`} />
            <div>
              <Label htmlFor="dry-run-switch" className="text-sm font-medium text-slate-200 cursor-pointer">
                Mode Test (Dry Run)
              </Label>
              <p className="text-xs text-slate-400 mt-0.5">
                {dryRun
                  ? "Simulation uniquement - Aucune action réelle"
                  : "⚠️ Mode Production - Actions réelles activées"}
              </p>
            </div>
          </div>
          <Switch
            id="dry-run-switch"
            checked={dryRun}
            onCheckedChange={setDryRun}
            className="data-[state=checked]:bg-amber-500"
          />
        </div>

        {/* Warning Banner when Dry Run is OFF */}
        {!dryRun && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-red-500/10 border border-red-500/30 animate-pulse">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-red-400 mb-1">
                ⚠️ Mode Production Activé
              </h4>
              <p className="text-xs text-red-200/80">
                Les bots vont effectuer de vraies actions (envoi de messages, visites de profils).
                Vérifiez la configuration avant de lancer.
              </p>
            </div>
          </div>
        )}

        {/* Bot Cards Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <BotCard
            type="birthday"
            title="Bot Anniversaires"
            icon={Gift}
            description="Messages du jour uniquement"
            color="pink"
            settingsLink="/settings?tab=birthday"
          />
          <BotCard
            type="unlimited"
            title="Bot Unlimited"
            icon={InfinityIcon}
            description="Jour + Retards (max 10j)"
            color="indigo"
            settingsLink="/settings?tab=birthday"
          />
          <BotCard
            type="visitor"
            title="Bot Visiteur"
            icon={Users}
            description="Visite automatique de profils"
            color="emerald"
            settingsLink="/settings?tab=visitor"
          />
        </div>

        {/* Status Footer */}
        {status?.active_jobs && status.active_jobs.length > 0 ? (
          <div className="text-center text-sm text-emerald-400 pt-2 border-t border-slate-800">
            ✓ {status.active_jobs.length} job{status.active_jobs.length > 1 ? 's' : ''} en cours d'exécution
          </div>
        ) : (
          <div className="text-center text-xs text-slate-500 pt-2 border-t border-slate-800">
            Système prêt - Aucun job en cours
          </div>
        )}
      </CardContent>
    </Card>
  )
}
