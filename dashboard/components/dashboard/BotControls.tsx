"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
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
  Infinity as InfinityIcon
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function BotControlsWidget() {
  const [status, setStatus] = useState<BotStatusDetailed | null>(null)
  const [loading, setLoading] = useState<string | null>(null) // 'birthday', 'visitor', 'stop-birthday', etc.
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

  const handleStart = async (type: 'birthday' | 'visitor' | 'unlimited') => {
    setLoading(type)
    try {
      if (type === 'birthday') {
        await startBot({ dryRun: false, processLate: false })
      } else if (type === 'unlimited') {
        await startBot({ dryRun: false, processLate: true })
      } else if (type === 'visitor') {
        await startVisitorBot({ dryRun: false, limit: 10 }) // Default limit, could be configurable
      }
      toast({ title: "Bot démarré", description: `Le bot ${type} a été lancé.` })
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

  const BotRow = ({
    type,
    title,
    icon: Icon,
    description
  }: {
    type: 'birthday' | 'visitor' | 'unlimited',
    title: string,
    icon: any,
    description: string
  }) => {
    // Mapping job_type 'birthday' to both Birthday and Unlimited widgets if they are just variations.
    // For now assuming 'birthday' covers both.
    const running = isRunning(type === 'unlimited' ? 'birthday' : type)
    const activeJobId = getJobId(type === 'unlimited' ? 'birthday' : type)
    const stopKey = `stop-${type}`

    return (
      <div className="flex items-center justify-between p-4 border rounded-lg bg-card/50 hover:bg-card/80 transition-colors">
        <div className="flex items-center gap-4">
          <div className={`p-2 rounded-full ${running ? "bg-green-500/10 text-green-500" : "bg-muted text-muted-foreground"}`}>
            <Icon className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="font-semibold">{title}</h3>
              {running ? (
                <Badge variant="default" className="bg-green-500 hover:bg-green-600 animate-pulse">
                  Running
                </Badge>
              ) : (
                <Badge variant="secondary" className="text-muted-foreground">
                  Idle
                </Badge>
              )}
            </div>
            <p className="text-sm text-muted-foreground">{description}</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          {running ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => handleStop(type === 'unlimited' ? 'birthday' : type, activeJobId)}
              disabled={loading === stopKey}
            >
              {loading === stopKey ? (
                <span className="animate-spin mr-2">⏳</span>
              ) : (
                <Square className="h-4 w-4 mr-2 fill-current" />
              )}
              Arrêt d'Urgence
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => handleStart(type)}
              disabled={!!loading || (status?.worker_status === 'working')}
            >
              {loading === type ? (
                 <span className="animate-spin mr-2">⏳</span>
              ) : (
                 <Play className="h-4 w-4 mr-2 fill-current" />
              )}
              Démarrer
            </Button>
          )}
        </div>
      </div>
    )
  }

  return (
    <Card className="w-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-5 w-5" />
          Pilotage des Bots
        </CardTitle>
        <CardDescription>
          Contrôle granulaire des processus d'automatisation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <BotRow
          type="birthday"
          title="Bot Anniversaires"
          icon={Gift}
          description="Envoie les messages du jour uniquement."
        />
        <BotRow
          type="unlimited"
          title="Bot Unlimited (Retard)"
          icon={InfinityIcon}
          description="Traite les messages du jour + retards (max 10j)."
        />
        <BotRow
          type="visitor"
          title="Bot Visiteur"
          icon={Users}
          description="Visite les profils ciblés pour générer du trafic."
        />

        {status?.active_jobs.length === 0 && (
          <div className="text-center text-xs text-muted-foreground mt-4">
             Le système est prêt. Aucun job en cours.
          </div>
        )}
      </CardContent>
    </Card>
  )
}
