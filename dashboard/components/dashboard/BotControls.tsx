"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
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
  Loader2
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function BotControlsWidget() {
  const [status, setStatus] = useState<BotStatusDetailed | null>(null)
  const [loading, setLoading] = useState<string | null>(null) // 'birthday', 'visitor', 'stop-birthday', etc.
  const [dryRun, setDryRun] = useState<boolean>(true) // Default to dry-run for safety
  const [visitorLimit, setVisitorLimit] = useState<string>("") // Empty string = use config default
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
        // Mode Standard: Respecte la configuration (process_today/late selon config)
        // Mais ici, le bouton s'appelle "Bot Anniversaires" (Jour uniquement selon description)
        // On force processLate: false pour être cohérent avec le bouton UI
        await startBot({ dryRun, processLate: false })
      } else if (type === 'unlimited') {
        // Mode Unlimited: Force le traitement des retards
        await startBot({ dryRun, processLate: true })
      } else if (type === 'visitor') {
        // Mode Visiteur: Utilise la configuration du fichier config.yaml par défaut,
        // ou la limite spécifiée par l'utilisateur.
        const limit = visitorLimit ? parseInt(visitorLimit, 10) : undefined
        await startVisitorBot({ dryRun, limit })
      }

      const mode = dryRun ? "test (dry-run)" : "production"
      toast({
        title: "Bot démarré",
        description: `Le bot ${type} a été lancé en mode ${mode}.`,
        variant: dryRun ? "default" : "default"
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

  const BotRow = ({
    type,
    title,
    icon: Icon,
    description,
    showLimitInput = false
  }: {
    type: 'birthday' | 'visitor' | 'unlimited',
    title: string,
    icon: any,
    description: string,
    showLimitInput?: boolean
  }) => {
    // Mapping job_type 'birthday' to both Birthday and Unlimited widgets if they are just variations.
    // For now assuming 'birthday' covers both.
    const running = isRunning(type === 'unlimited' ? 'birthday' : type)
    const activeJobId = getJobId(type === 'unlimited' ? 'birthday' : type)
    const stopKey = `stop-${type}`
    const limitInputId = `limit-input-${type}`

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
          {showLimitInput && !running && (
             <div className="flex items-center gap-2 mr-2">
               <Label htmlFor={limitInputId} className="text-xs text-muted-foreground whitespace-nowrap">
                 Limite (opt.)
               </Label>
               <Input
                 id={limitInputId}
                 type="number"
                 placeholder="Défaut"
                 className="w-20 h-8 text-xs bg-slate-950 border-slate-700"
                 value={visitorLimit}
                 onChange={(e) => setVisitorLimit(e.target.value)}
                 min={1}
               />
             </div>
          )}

          {running ? (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => handleStop(type === 'unlimited' ? 'birthday' : type, activeJobId)}
              disabled={loading === stopKey}
              aria-label={`Arrêt d'urgence ${title}`}
            >
              {loading === stopKey ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Square className="h-4 w-4 mr-2 fill-current" />
              )}
              Arrêt d&apos;Urgence
            </Button>
          ) : (
            <Button
              variant="default"
              size="sm"
              onClick={() => handleStart(type)}
              disabled={!!loading || (status?.worker_status === 'working')}
              aria-label={`Démarrer ${title}`}
            >
              {loading === type ? (
                 <Loader2 className="h-4 w-4 mr-2 animate-spin" />
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
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-slate-200">
          <Activity className="h-5 w-5 text-blue-500" />
          Pilotage des Bots
        </CardTitle>
        <CardDescription>
          Contrôle granulaire des processus d&apos;automatisation
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Dry Run Toggle */}
        <div className="flex items-center justify-between p-4 rounded-lg bg-slate-800/50 border border-slate-700">
          <div className="flex items-center gap-3">
            <AlertTriangle className={`h-5 w-5 ${dryRun ? 'text-yellow-500' : 'text-slate-500'}`} />
            <div>
              <Label htmlFor="dry-run-switch" className="text-sm font-medium text-slate-200 cursor-pointer">
                Mode Test (Dry Run)
              </Label>
              <p className="text-xs text-slate-400 mt-0.5">
                {dryRun
                  ? "Aucune action réelle ne sera effectuée"
                  : "⚠️ Les bots enverront de vrais messages"}
              </p>
            </div>
          </div>
          <Switch
            id="dry-run-switch"
            checked={dryRun}
            onCheckedChange={setDryRun}
            className="data-[state=checked]:bg-yellow-500"
          />
        </div>

        {/* Warning Banner when Dry Run is OFF */}
        {!dryRun && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/30">
            <AlertTriangle className="h-5 w-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <h4 className="text-sm font-semibold text-yellow-500 mb-1">
                ⚠️ Mode Production Activé
              </h4>
              <p className="text-xs text-yellow-200/80">
                Les bots vont effectuer de vraies actions (envoi de messages, visites de profils).
                Assurez-vous que la configuration est correcte avant de lancer.
              </p>
            </div>
          </div>
        )}

        {/* Bot Control Rows */}
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
          description="Visite les profils selon config.yaml."
          showLimitInput={true}
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
