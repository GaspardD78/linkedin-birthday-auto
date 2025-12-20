"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { X, Loader2, AlertCircle, CheckCircle, XCircle, Clock } from "lucide-react"
import { JobExecutionLog } from "@/types/scheduler"
import { getJobHistory } from "@/lib/scheduler-api"

interface JobHistoryDialogProps {
  jobId: string
  jobName: string
  onClose: () => void
}

export function JobHistoryDialog({ jobId, jobName, onClose }: JobHistoryDialogProps) {
  const [history, setHistory] = useState<JobExecutionLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadHistory()
  }, [jobId])

  const loadHistory = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await getJobHistory(jobId, 50)
      setHistory(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />
      case 'running':
        return <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
      default:
        return <Clock className="h-4 w-4 text-slate-400" />
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'completed':
        return <Badge className="bg-green-900/50 text-green-300 border-green-700">Terminé</Badge>
      case 'failed':
        return <Badge variant="destructive">Échec</Badge>
      case 'running':
        return <Badge className="bg-blue-900/50 text-blue-300 border-blue-700">En cours</Badge>
      default:
        return <Badge variant="outline">{status}</Badge>
    }
  }

  const formatDuration = (startedAt: string, completedAt?: string) => {
    if (!completedAt) return 'En cours...'

    const start = new Date(startedAt).getTime()
    const end = new Date(completedAt).getTime()
    const seconds = Math.floor((end - start) / 1000)

    if (seconds < 60) return `${seconds}s`
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}m ${remainingSeconds}s`
  }

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <Card className="bg-slate-900 border-slate-800 w-full max-w-4xl max-h-[90vh] flex flex-col">
        <CardHeader className="border-b border-slate-800">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-slate-200">Historique d&apos;Exécution</CardTitle>
              <p className="text-sm text-slate-400 mt-1">{jobName}</p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:bg-slate-800"
            >
              <X className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-y-auto p-6">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="ml-3 text-slate-400">Chargement de l&apos;historique...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <AlertCircle className="h-12 w-12 mx-auto mb-3 text-red-400" />
              <p className="text-red-400">{error}</p>
            </div>
          ) : history.length === 0 ? (
            <div className="text-center py-12">
              <Clock className="h-12 w-12 mx-auto mb-3 text-slate-600" />
              <p className="text-slate-400">Aucune exécution enregistrée</p>
            </div>
          ) : (
            <div className="space-y-3">
              {history.map((log) => (
                <div
                  key={log.id}
                  className="bg-slate-950 border border-slate-800 rounded-lg p-4 hover:border-slate-700 transition-colors"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(log.status)}
                      <span className="text-sm font-medium text-slate-300">
                        {new Date(log.started_at).toLocaleString('fr-FR')}
                      </span>
                    </div>
                    {getStatusBadge(log.status)}
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-3 text-xs">
                    <div>
                      <span className="text-slate-500">Déclencheur</span>
                      <p className="text-slate-300 font-medium">
                        {log.trigger_type === 'manual' ? '🖱️ Manuel' : '⏰ Planifié'}
                      </p>
                    </div>
                    <div>
                      <span className="text-slate-500">Durée</span>
                      <p className="text-slate-300 font-medium">
                        {formatDuration(log.started_at, log.completed_at)}
                      </p>
                    </div>
                    {log.rq_job_id && (
                      <div>
                        <span className="text-slate-500">RQ Job ID</span>
                        <p className="text-slate-300 font-mono text-[10px]">
                          {log.rq_job_id.substring(0, 12)}...
                        </p>
                      </div>
                    )}
                    {log.result_summary && (
                      <div>
                        <span className="text-slate-500">Résumé</span>
                        <p className="text-slate-300 font-medium">
                          {log.result_summary}
                        </p>
                      </div>
                    )}
                  </div>

                  {log.error_message && (
                    <div className="mt-3 p-2 bg-red-950/30 border border-red-800 rounded text-xs">
                      <p className="text-red-300 font-mono">{log.error_message}</p>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
