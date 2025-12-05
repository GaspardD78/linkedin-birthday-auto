"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Users,
  StopCircle,
  AlertTriangle,
  RefreshCw,
  Activity,
  CheckCircle,
  XCircle,
  Clock
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { getWorkersStatus, stopBot, getBotStatusDetailed } from "@/lib/api"

interface WorkerInfo {
  name: string
  state: string
  current_job: string | null
  successful_jobs: number
  failed_jobs: number
  total_working_time: number
}

interface WorkersStatusResponse {
  workers: WorkerInfo[]
  total_workers: number
}

interface JobStatus {
  id: string
  status: string
  type: string
  enqueued_at: string
  started_at?: string
}

export function WorkerManagementPanel() {
  const [workersStatus, setWorkersStatus] = useState<WorkersStatusResponse | null>(null)
  const [activeJobs, setActiveJobs] = useState<JobStatus[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const { toast } = useToast()

  const refreshStatus = async () => {
    try {
      const [workers, botStatus] = await Promise.all([
        getWorkersStatus(),
        getBotStatusDetailed()
      ])
      setWorkersStatus(workers)
      setActiveJobs(botStatus.active_jobs || [])
    } catch (error) {
      console.error("Failed to fetch workers status", error)
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const handleStopJob = async (jobId: string, jobType: string) => {
    const actionKey = `stop-${jobId}`
    setLoading(actionKey)
    try {
      await stopBot(jobType, jobId)
      toast({
        title: "Job arrêté",
        description: `Le job ${jobType} a été arrêté`,
      })
      await refreshStatus()
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setLoading(null)
    }
  }

  const handleStopAll = async () => {
    setLoading("stop-all")
    try {
      await stopBot("", "") // Empty parameters = stop all
      toast({
        title: "Arrêt d'urgence",
        description: "Tous les workers ont été arrêtés",
      })
      await refreshStatus()
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setLoading(null)
    }
  }

  const formatDuration = (seconds: number): string => {
    if (!seconds || seconds === 0) return "0s"
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = Math.floor(seconds % 60)

    if (hours > 0) return `${hours}h ${minutes}m`
    if (minutes > 0) return `${minutes}m ${secs}s`
    return `${secs}s`
  }

  const formatTimestamp = (timestamp: string): string => {
    if (!timestamp) return "N/A"
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    } catch {
      return "N/A"
    }
  }

  const getJobTypeColor = (type: string) => {
    switch (type) {
      case "birthday":
        return "bg-pink-600"
      case "visit":
        return "bg-emerald-600"
      default:
        return "bg-slate-600"
    }
  }

  if (!workersStatus) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Users className="h-5 w-5 text-cyan-500" />
            Gestion des Workers
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Users className="h-5 w-5 text-cyan-500" />
              Gestion des Workers
            </CardTitle>
            <CardDescription className="mt-1">
              Supervision et contrôle des workers RQ
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={refreshStatus}
              className="border-slate-700"
            >
              <RefreshCw className="h-4 w-4" />
            </Button>
            {activeJobs.length > 0 && (
              <Button
                variant="destructive"
                size="sm"
                onClick={handleStopAll}
                disabled={loading === "stop-all"}
              >
                {loading === "stop-all" ? (
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                ) : (
                  <StopCircle className="h-4 w-4 mr-2" />
                )}
                Arrêt d'urgence
              </Button>
            )}
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Workers Summary */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Workers Actifs</p>
                  <p className="text-2xl font-bold text-slate-200">
                    {workersStatus.total_workers}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-cyan-500" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 mb-1">Jobs Actifs</p>
                  <p className="text-2xl font-bold text-slate-200">
                    {activeJobs.length}
                  </p>
                </div>
                <Activity className="h-8 w-8 text-emerald-500 animate-pulse" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-800/50 border-slate-700">
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-slate-400 mb-1">État Global</p>
                  <p className="text-lg font-semibold text-slate-200">
                    {activeJobs.length > 0 ? (
                      <Badge className="bg-emerald-600">En cours</Badge>
                    ) : (
                      <Badge variant="secondary">Idle</Badge>
                    )}
                  </p>
                </div>
                {activeJobs.length > 0 ? (
                  <CheckCircle className="h-8 w-8 text-emerald-500" />
                ) : (
                  <Clock className="h-8 w-8 text-slate-500" />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Active Jobs */}
        {activeJobs.length > 0 ? (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Activity className="h-4 w-4 text-emerald-500 animate-pulse" />
              Jobs en Cours
            </h3>
            {activeJobs.map((job) => (
              <Card key={job.id} className="bg-slate-800/50 border-slate-700">
                <CardContent className="pt-4">
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1 space-y-2">
                      <div className="flex items-center gap-2">
                        <Badge className={getJobTypeColor(job.type)}>
                          {job.type}
                        </Badge>
                        <span className="text-xs font-mono text-slate-400">
                          {job.id.substring(0, 8)}...
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-xs">
                        <div>
                          <span className="text-slate-500">Mis en queue:</span>
                          <span className="ml-2 text-slate-300 font-mono">
                            {formatTimestamp(job.enqueued_at)}
                          </span>
                        </div>
                        {job.started_at && (
                          <div>
                            <span className="text-slate-500">Démarré:</span>
                            <span className="ml-2 text-slate-300 font-mono">
                              {formatTimestamp(job.started_at)}
                            </span>
                          </div>
                        )}
                      </div>
                    </div>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleStopJob(job.id, job.type)}
                      disabled={loading === `stop-${job.id}`}
                    >
                      {loading === `stop-${job.id}` ? (
                        <RefreshCw className="h-4 w-4 animate-spin" />
                      ) : (
                        <StopCircle className="h-4 w-4" />
                      )}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center py-8 text-slate-500">
            <div className="text-center">
              <Clock className="h-12 w-12 mx-auto mb-2 text-slate-600" />
              <p className="text-sm">Aucun job actif</p>
            </div>
          </div>
        )}

        {/* Worker Details */}
        {workersStatus.workers.length > 0 && (
          <div className="space-y-3">
            <h3 className="text-sm font-semibold text-slate-200 flex items-center gap-2">
              <Users className="h-4 w-4 text-cyan-500" />
              Détails des Workers
            </h3>
            {workersStatus.workers.map((worker, index) => (
              <Card key={index} className="bg-slate-800/50 border-slate-700">
                <CardContent className="pt-4">
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-medium text-slate-200">
                        {worker.name}
                      </span>
                      <Badge variant={worker.state === "busy" ? "default" : "secondary"}>
                        {worker.state}
                      </Badge>
                    </div>
                    <div className="grid grid-cols-3 gap-4 text-xs">
                      <div>
                        <span className="text-slate-500">Succès:</span>
                        <span className="ml-2 text-emerald-400 font-semibold">
                          {worker.successful_jobs}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Échecs:</span>
                        <span className="ml-2 text-red-400 font-semibold">
                          {worker.failed_jobs}
                        </span>
                      </div>
                      <div>
                        <span className="text-slate-500">Temps total:</span>
                        <span className="ml-2 text-slate-300 font-mono">
                          {formatDuration(worker.total_working_time)}
                        </span>
                      </div>
                    </div>
                    {worker.current_job && (
                      <div className="mt-2 p-2 rounded bg-slate-900/50 border border-slate-700">
                        <span className="text-xs text-slate-400">Job actuel:</span>
                        <span className="ml-2 text-xs text-slate-300 font-mono">
                          {worker.current_job.substring(0, 16)}...
                        </span>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {/* No workers warning */}
        {workersStatus.total_workers === 0 && (
          <div className="flex items-start gap-3 p-4 rounded-lg bg-amber-500/10 border border-amber-500/30">
            <AlertTriangle className="h-5 w-5 text-amber-500 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-amber-400 mb-1">
                Aucun worker actif
              </h4>
              <p className="text-xs text-amber-200/80">
                Aucun worker RQ n'est actuellement en cours d'exécution.
                Vérifiez que le service worker est démarré.
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
