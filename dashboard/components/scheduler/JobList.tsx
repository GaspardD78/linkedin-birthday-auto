"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Switch } from "@/components/ui/switch"
import {
  Calendar,
  Clock,
  Play,
  Pencil,
  Trash2,
  History,
  Loader2,
  AlertCircle,
  Plus
} from "lucide-react"
import {
  ScheduledJob,
  formatSchedule,
  getBotModeDisplay,
  getDryRunBadge
} from "@/types/scheduler"
import { listJobs, toggleJob, runJobNow, deleteJob } from "@/lib/scheduler-api"
import { useToast } from "@/components/ui/use-toast"
import { JobHistoryDialog } from "./JobHistoryDialog"

interface JobListProps {
  onCreateJob: () => void
  onEditJob: (job: ScheduledJob) => void
  refreshTrigger?: number
}

export function JobList({ onCreateJob, onEditJob, refreshTrigger }: JobListProps) {
  const [jobs, setJobs] = useState<ScheduledJob[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionInProgress, setActionInProgress] = useState<string | null>(null)
  const [historyJobId, setHistoryJobId] = useState<string | null>(null)
  const { toast } = useToast()

  const loadJobs = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await listJobs(false)
      setJobs(data)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load jobs'
      setError(message)
      toast({
        variant: "destructive",
        title: "Erreur",
        description: message
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadJobs()
  }, [refreshTrigger])

  const handleToggle = async (job: ScheduledJob) => {
    setActionInProgress(job.id)
    try {
      const updated = await toggleJob(job.id, !job.enabled)
      setJobs(jobs.map(j => j.id === job.id ? updated : j))
      toast({
        title: updated.enabled ? "Job activé" : "Job désactivé",
        description: `"${updated.name}" est maintenant ${updated.enabled ? 'actif' : 'inactif'}.`
      })
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err instanceof Error ? err.message : 'Failed to toggle job'
      })
    } finally {
      setActionInProgress(null)
    }
  }

  const handleRunNow = async (job: ScheduledJob) => {
    setActionInProgress(job.id)
    try {
      await runJobNow(job.id)
      toast({
        title: "Job démarré",
        description: `"${job.name}" a été déclenché manuellement.`
      })
      // Refresh to update last_run_at
      await loadJobs()
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err instanceof Error ? err.message : 'Failed to run job'
      })
    } finally {
      setActionInProgress(null)
    }
  }

  const handleDelete = async (job: ScheduledJob) => {
    if (!confirm(`Supprimer le job "${job.name}" ? Cette action est irréversible.`)) {
      return
    }

    setActionInProgress(job.id)
    try {
      await deleteJob(job.id)
      setJobs(jobs.filter(j => j.id !== job.id))
      toast({
        title: "Job supprimé",
        description: `"${job.name}" a été supprimé avec succès.`
      })
    } catch (err) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: err instanceof Error ? err.message : 'Failed to delete job'
      })
    } finally {
      setActionInProgress(null)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
        <span className="ml-3 text-slate-400">Chargement des jobs...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="text-center py-12">
        <AlertCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
        <p className="text-red-400 mb-4">{error}</p>
        <Button onClick={loadJobs} variant="outline">Réessayer</Button>
      </div>
    )
  }

  if (jobs.length === 0) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="py-12 text-center">
          <Calendar className="h-16 w-16 mx-auto mb-4 text-slate-600" />
          <h3 className="text-xl font-semibold text-slate-300 mb-2">Aucun job programmé</h3>
          <p className="text-slate-400 mb-6">
            Créez votre premier job d'automatisation pour planifier l'exécution de vos bots.
          </p>
          <Button onClick={onCreateJob} className="bg-blue-600 hover:bg-blue-700">
            <Plus className="h-4 w-4 mr-2" />
            Créer un Job
          </Button>
        </CardContent>
      </Card>
    )
  }

  return (
    <>
      <div className="space-y-4">
        {jobs.map(job => (
          <Card key={job.id} className="bg-slate-900 border-slate-800">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <CardTitle className="text-slate-200">{job.name}</CardTitle>
                    <Badge variant={job.bot_type === 'birthday' ? 'default' : 'secondary'}>
                      {job.bot_type === 'birthday' ? '🎂 Birthday' : '👁️ Visitor'}
                    </Badge>
                    {getDryRunBadge(job)}
                    {!job.enabled && (
                      <Badge variant="outline" className="border-slate-600 text-slate-400">
                        Désactivé
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-slate-400">
                    {getBotModeDisplay(job)}
                  </CardDescription>
                </div>
                <Switch
                  checked={job.enabled}
                  onCheckedChange={() => handleToggle(job)}
                  disabled={actionInProgress === job.id}
                  className="ml-4"
                />
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Schedule Info */}
                <div className="flex items-center gap-6 text-sm">
                  <div className="flex items-center gap-2 text-slate-300">
                    <Clock className="h-4 w-4 text-blue-400" />
                    <span className="font-medium">{formatSchedule(job)}</span>
                  </div>
                  {job.next_run_at && (
                    <div className="flex items-center gap-2 text-slate-400">
                      <Calendar className="h-4 w-4" />
                      <span className="text-xs">
                        Prochaine: {new Date(job.next_run_at).toLocaleString('fr-FR')}
                      </span>
                    </div>
                  )}
                </div>

                {/* Last Run */}
                {job.last_run_at && (
                  <div className="text-xs text-slate-500">
                    Dernière exécution: {new Date(job.last_run_at).toLocaleString('fr-FR')}
                    {job.last_run_status && (
                      <Badge
                        variant={job.last_run_status === 'completed' ? 'default' : 'destructive'}
                        className="ml-2"
                      >
                        {job.last_run_status}
                      </Badge>
                    )}
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-slate-800">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleRunNow(job)}
                    disabled={actionInProgress === job.id}
                    className="border-slate-700 hover:bg-slate-800"
                  >
                    {actionInProgress === job.id ? (
                      <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                    ) : (
                      <Play className="h-3 w-3 mr-1" />
                    )}
                    Exécuter
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onEditJob(job)}
                    disabled={actionInProgress === job.id}
                    className="border-slate-700 hover:bg-slate-800"
                  >
                    <Pencil className="h-3 w-3 mr-1" />
                    Modifier
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setHistoryJobId(job.id)}
                    className="border-slate-700 hover:bg-slate-800"
                  >
                    <History className="h-3 w-3 mr-1" />
                    Historique
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => handleDelete(job)}
                    disabled={actionInProgress === job.id}
                    className="border-red-700 hover:bg-red-950 text-red-400 ml-auto"
                  >
                    <Trash2 className="h-3 w-3 mr-1" />
                    Supprimer
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* History Dialog */}
      {historyJobId && (
        <JobHistoryDialog
          jobId={historyJobId}
          jobName={jobs.find(j => j.id === historyJobId)?.name || ''}
          onClose={() => setHistoryJobId(null)}
        />
      )}
    </>
  )
}
