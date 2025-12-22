"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  getBotStatusDetailed,
  startBot,
  startVisitorBot,
  startInvitationBot,
  stopBot,
  BotStatusDetailed
} from "@/lib/api"
import {
  Play,
  Square,
  Activity,
  Gift,
  Users,
  Trash2,
  AlertTriangle,
  Loader2
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"

export function BotControlsWidget() {
  const [status, setStatus] = useState<BotStatusDetailed | null>(null)
  const [loading, setLoading] = useState<string | null>(null)
  // Default Dry Run to false as requested
  const [dryRun, setDryRun] = useState<boolean>(false)
  const [visitorLimit, setVisitorLimit] = useState<string>("")
  const [birthdayMode, setBirthdayMode] = useState<"standard" | "unlimited">("standard")
  const { toast } = useToast()

  const refreshStatus = async () => {
    try {
      const data = await getBotStatusDetailed()
      setStatus(data)
    } catch (error) {
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  const isRunning = (type: string) => {
    // Check main type or subtypes (e.g. birthday covers unlimited)
    if (type === 'birthday') {
      return status?.active_jobs.some(job => job.type === 'birthday')
    }
    return status?.active_jobs.some(job => job.type === type)
  }

  const getJobId = (type: string) => {
    if (type === 'birthday') {
      return status?.active_jobs.find(job => job.type === 'birthday')?.id
    }
    return status?.active_jobs.find(job => job.type === type)?.id
  }

  const handleStart = async (type: 'birthday' | 'visitor' | 'invitation_manager') => {
    setLoading(type)
    try {
      if (type === 'birthday') {
        // Send 'birthday' type for both modes, but toggle processLate based on selection
        const processLate = birthdayMode === 'unlimited'
        await startBot({ dryRun, processLate })
      } else if (type === 'visitor') {
        const limit = visitorLimit ? parseInt(visitorLimit, 10) : undefined
        await startVisitorBot({ dryRun, limit })
      } else if (type === 'invitation_manager') {
        await startInvitationBot({ dryRun })
      }

      const modeText = dryRun ? "test (dry-run)" : "production"
      toast({
        title: "Bot démarré",
        description: `Le bot ${type} a été lancé en mode ${modeText}.`,
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

  // --- Bot Row Component ---
  const BotRow = ({
    type,
    title,
    icon: Icon,
    description,
    showLimitInput = false,
    showBirthdaySelect = false
  }: {
    type: 'birthday' | 'visitor' | 'invitation_manager',
    title: string,
    icon: any,
    description: string,
    showLimitInput?: boolean
    showBirthdaySelect?: boolean
  }) => {
    const running = isRunning(type)
    const activeJobId = getJobId(type)
    const stopKey = `stop-${type}`
    const limitInputId = `limit-input-${type}`

    return (
      <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border rounded-lg bg-card/50 hover:bg-card/80 transition-colors gap-4">
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

        <div className="flex items-center gap-2 self-end sm:self-auto">
            {/* Birthday Mode Select */}
            {showBirthdaySelect && !running && (
                <div className="w-[140px] mr-2">
                    <Select
                        value={birthdayMode}
                        onValueChange={(v: "standard" | "unlimited") => setBirthdayMode(v)}
                    >
                        <SelectTrigger className="h-8 text-xs bg-slate-950 border-slate-700">
                            <SelectValue placeholder="Mode" />
                        </SelectTrigger>
                        <SelectContent>
                            <SelectItem value="standard">Standard (Jour)</SelectItem>
                            <SelectItem value="unlimited">Rattrapage</SelectItem>
                        </SelectContent>
                    </Select>
                </div>
            )}

            {/* Visitor Limit Input */}
            {showLimitInput && !running && (
             <div className="flex items-center gap-2 mr-2">
               <Label htmlFor={limitInputId} className="text-xs text-muted-foreground whitespace-nowrap hidden md:block">
                 Limite
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
              onClick={() => handleStop(type, activeJobId)}
              disabled={loading === stopKey}
              aria-label={`Arrêt d'urgence ${title}`}
            >
              {loading === stopKey ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Square className="h-4 w-4 mr-2 fill-current" />
              )}
              Arrêt
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
        <div className={`flex items-center justify-between p-4 rounded-lg border transition-colors ${dryRun ? 'bg-yellow-500/10 border-yellow-500/30' : 'bg-slate-800/50 border-slate-700'}`}>
          <div className="flex items-center gap-3">
             {dryRun ? (
                 <AlertTriangle className="h-5 w-5 text-yellow-500" />
             ) : (
                 <Activity className="h-5 w-5 text-slate-500" />
             )}
            <div>
              <Label htmlFor="dry-run-switch" className="text-sm font-medium text-slate-200 cursor-pointer">
                {dryRun ? "Mode Test (Dry Run)" : "Mode Production"}
              </Label>
              <p className={`text-xs mt-0.5 ${dryRun ? "text-yellow-200/80" : "text-slate-400"}`}>
                {dryRun
                  ? "⚠️ Aucune action réelle (Simulation)"
                  : "Les actions (messages, retraits) sont réelles"}
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

        {/* Bot Control Rows */}
        <BotRow
          type="birthday"
          title="Bot Anniversaires"
          icon={Gift}
          description="Envoie les souhaits d'anniversaire."
          showBirthdaySelect={true}
        />
        <BotRow
          type="visitor"
          title="Bot Visiteur"
          icon={Users}
          description="Visite les profils cibles."
          showLimitInput={true}
        />
        <BotRow
          type="invitation_manager"
          title="Nettoyage Invitations"
          icon={Trash2}
          description="Retire les invitations anciennes."
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
