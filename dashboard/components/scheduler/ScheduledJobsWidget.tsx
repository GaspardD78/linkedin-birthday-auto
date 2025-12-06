"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Calendar,
  Clock,
  Play,
  Settings,
  RefreshCw,
  Loader2,
  AlertCircle
} from "lucide-react"
import {
  ScheduledJob,
  formatSchedule,
  getBotModeDisplay,
  getDryRunBadge
} from "@/types/scheduler"
import { listJobs, runJobNow } from "@/lib/scheduler-api"
import { useToast } from "@/components/ui/use-toast"
import Link from "next/link"

export function ScheduledJobsWidget() {
  const [jobs, setJobs] = useState<ScheduledJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [runningJobId, setRunningJobId] = useState<string | null>(null)
  const { toast } = useToast()

  const loadJobs = async () => {
    setError(null)
    try {
      // Get only enabled jobs, limit to 3 for widget display
      const data = await listJobs(true)
      setJobs(data.slice(0, 3))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load jobs')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
    // Auto-refresh every 10 seconds
    const interval = setInterval(loadJobs, 10000)
    return () => clearInterval(interval)
  }, [])

  const handleRunNow = async (job: ScheduledJob) => {
    setRunningJobId(job.id)
    try {
      await runJobNow(job.id)
      toast({
        title: "Job démarré",
        description: `"${job.name}" a été déclenché manuellement.`
      })
      // Refresh jobs
      await loadJobs()
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err instanceof Error ? err.message : 'Failed to run job'
      })
    } finally {
      setRunningJobId(null)
    }
  }

  if (loading) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Calendar className="h-5 w-5 text-cyan-500" />
            Jobs Programmés
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

  if (error) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800 border-red-500/20">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Calendar className="h-5 w-5 text-cyan-500" />
            Jobs Programmés
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col items-center justify-center py-6 text-center">
            <AlertCircle className="h-8 w-8 text-red-400 mb-2" />
            <p className="text-sm text-red-400 mb-3">{error}</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => {
                setLoading(true)
                loadJobs()
              }}
              className="border-slate-700 hover:bg-slate-800"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Réessayer
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (jobs.length === 0) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Calendar className="h-5 w-5 text-cyan-500" />
              Jobs Programmés
            </CardTitle>
            <Link href="/settings?tab=automation">
              <Button variant="outline" size="sm" className="border-slate-700 hover:bg-slate-800">
                <Settings className="h-3 w-3 mr-1" />
                Configurer
              </Button>
            </Link>
          </div>
        </CardHeader>
        <CardContent>
          <div className="text-center py-6">
            <Calendar className="h-12 w-12 mx-auto mb-3 text-slate-600" />
            <p className="text-sm text-slate-400 mb-3">Aucun job actif</p>
            <Link href="/settings?tab=automation">
              <Button size="sm" className="bg-cyan-600 hover:bg-cyan-700">
                Créer un Job
              </Button>
            </Link>
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Calendar className="h-5 w-5 text-cyan-500" />
            Jobs Programmés
          </CardTitle>
          <Link href="/settings?tab=automation">
            <Button variant="outline" size="sm" className="border-slate-700 hover:bg-slate-800">
              <Settings className="h-3 w-3 mr-1" />
              Gérer
            </Button>
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {jobs.map((job) => (
            <div
              key={job.id}
              className="bg-slate-950 border border-slate-800 rounded-lg p-3 hover:border-slate-700 transition-colors"
            >
              <div className="flex items-start justify-between mb-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <h4 className="text-sm font-medium text-slate-300 truncate">
                      {job.name}
                    </h4>
                    <Badge
                      variant={job.bot_type === 'birthday' ? 'default' : 'secondary'}
                      className="text-xs"
                    >
                      {job.bot_type === 'birthday' ? '🎂' : '👁️'}
                    </Badge>
                    {getDryRunBadge(job)}
                  </div>
                  <p className="text-xs text-slate-500 truncate">
                    {getBotModeDisplay(job)}
                  </p>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => handleRunNow(job)}
                  disabled={runningJobId === job.id}
                  className="h-7 px-2 hover:bg-slate-800 flex-shrink-0 ml-2"
                >
                  {runningJobId === job.id ? (
                    <Loader2 className="h-3 w-3 animate-spin" />
                  ) : (
                    <Play className="h-3 w-3" />
                  )}
                </Button>
              </div>

              <div className="flex items-center gap-4 text-xs text-slate-400">
                <div className="flex items-center gap-1">
                  <Clock className="h-3 w-3" />
                  <span>{formatSchedule(job)}</span>
                </div>
                {job.next_run_at && (
                  <div className="flex items-center gap-1 truncate">
                    <Calendar className="h-3 w-3" />
                    <span className="truncate">
                      {new Date(job.next_run_at).toLocaleString('fr-FR', {
                        day: '2-digit',
                        month: '2-digit',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </span>
                  </div>
                )}
              </div>
            </div>
          ))}

          {jobs.length === 3 && (
            <Link href="/settings?tab=automation">
              <Button
                variant="ghost"
                size="sm"
                className="w-full text-xs text-slate-400 hover:text-slate-300"
              >
                Voir tous les jobs →
              </Button>
            </Link>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
