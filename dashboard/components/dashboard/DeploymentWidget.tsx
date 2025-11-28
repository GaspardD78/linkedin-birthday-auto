"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Rocket,
  Server,
  Database,
  Activity,
  RefreshCw,
  Trash2,
  GitPullRequest,
  Package,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Loader2,
  Settings,
  Clock
} from "lucide-react"
import { useState, useEffect } from "react"

interface Service {
  name: string
  status: string
  uptime?: string
  memory_usage?: string
  cpu_usage?: string
}

interface Job {
  job_id: string
  status: string
  created_at: string
  started_at?: string
  ended_at?: string
  result?: string
  exc_info?: string
}

interface JobsData {
  queued: Job[]
  started: Job[]
  finished: Job[]
  failed: Job[]
  total: number
}

export function DeploymentWidget() {
  const [services, setServices] = useState<Service[]>([])
  const [jobs, setJobs] = useState<JobsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  // Récupérer le statut des services
  const fetchServicesStatus = async () => {
    try {
      const response = await fetch('/api/deployment/services')
      if (response.ok) {
        const data = await response.json()
        setServices(data.services || [])
      }
    } catch (error) {
      console.error('Failed to fetch services status:', error)
    }
  }

  // Récupérer la liste des jobs
  const fetchJobs = async () => {
    try {
      const response = await fetch('/api/deployment/jobs')
      if (response.ok) {
        const data = await response.json()
        setJobs(data)
      }
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    }
  }

  // Charger les données
  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchServicesStatus(), fetchJobs()])
      setLoading(false)
    }

    loadData()
    const interval = setInterval(loadData, 10000) // Refresh toutes les 10s

    return () => clearInterval(interval)
  }, [])

  // Exécuter une action de maintenance
  const handleMaintenance = async (action: string) => {
    setActionLoading(action)
    try {
      const response = await fetch('/api/deployment/maintenance', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action })
      })

      const data = await response.json()

      if (response.ok) {
        alert(`✅ ${data.message}`)
        // Rafraîchir les données
        await Promise.all([fetchServicesStatus(), fetchJobs()])
      } else {
        alert(`❌ Erreur : ${data.message || 'Une erreur est survenue'}`)
      }
    } catch (error) {
      console.error('Maintenance action failed:', error)
      alert('❌ Erreur de communication avec le serveur')
    } finally {
      setActionLoading(null)
    }
  }

  // Exécuter une action de déploiement
  const handleDeployment = async (action: string, service?: string) => {
    if (!confirm(`⚠️ Voulez-vous vraiment exécuter : ${action} ${service ? `(${service})` : ''} ?\n\nCette action peut interrompre le service.`)) {
      return
    }

    setActionLoading(action)
    try {
      const response = await fetch('/api/deployment/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, service })
      })

      const data = await response.json()

      if (response.ok && data.status === 'success') {
        alert(`✅ ${data.message}\n\n${data.output || ''}`)
      } else {
        alert(`⚠️ ${data.message}\n\n${data.output || ''}`)
      }
    } catch (error) {
      console.error('Deployment action failed:', error)
      alert('❌ Erreur de communication avec le serveur')
    } finally {
      setActionLoading(null)
    }
  }

  // Icône de statut
  const StatusIcon = ({ status }: { status: string }) => {
    switch (status) {
      case 'running':
        return <CheckCircle2 className="h-4 w-4 text-emerald-400" />
      case 'stopped':
        return <XCircle className="h-4 w-4 text-slate-500" />
      case 'error':
        return <AlertTriangle className="h-4 w-4 text-red-400" />
      default:
        return <Activity className="h-4 w-4 text-slate-400" />
    }
  }

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800 shadow-xl">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <Rocket className="h-5 w-5 text-purple-400" />
            Déploiement & Maintenance
          </CardTitle>
        </CardHeader>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-purple-400" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800 shadow-xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <Rocket className="h-5 w-5 text-purple-400" />
          Déploiement & Maintenance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">

        {/* Section 1: Status des Services */}
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Server className="h-4 w-4 text-blue-400" />
            <h3 className="font-semibold text-sm text-slate-200">Services Docker</h3>
          </div>
          <div className="space-y-2">
            {services.map((service, index) => (
              <div key={index} className="flex items-center justify-between text-sm">
                <div className="flex items-center gap-2">
                  <StatusIcon status={service.status} />
                  <span className="text-slate-300">{service.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {service.uptime && (
                    <span className="text-xs text-slate-500">{service.uptime}</span>
                  )}
                  <Badge
                    variant={service.status === 'running' ? 'default' : 'secondary'}
                    className={
                      service.status === 'running'
                        ? 'bg-emerald-600/20 text-emerald-400 border-emerald-600/50'
                        : service.status === 'error'
                        ? 'bg-red-600/20 text-red-400 border-red-600/50'
                        : 'bg-slate-600/20 text-slate-400 border-slate-600/50'
                    }
                  >
                    {service.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Section 2: Jobs en Cours */}
        {jobs && (
          <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-amber-400" />
                <h3 className="font-semibold text-sm text-slate-200">Jobs RQ</h3>
              </div>
              <Badge className="bg-slate-700 text-slate-200">
                {jobs.total} total
              </Badge>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div className="flex items-center justify-between bg-slate-800/50 rounded p-2">
                <span className="text-xs text-slate-400">En attente</span>
                <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/50">
                  {jobs.queued.length}
                </Badge>
              </div>
              <div className="flex items-center justify-between bg-slate-800/50 rounded p-2">
                <span className="text-xs text-slate-400">En cours</span>
                <Badge className="bg-amber-600/20 text-amber-400 border-amber-600/50">
                  {jobs.started.length}
                </Badge>
              </div>
              <div className="flex items-center justify-between bg-slate-800/50 rounded p-2">
                <span className="text-xs text-slate-400">Terminés</span>
                <Badge className="bg-emerald-600/20 text-emerald-400 border-emerald-600/50">
                  {jobs.finished.length}
                </Badge>
              </div>
              <div className="flex items-center justify-between bg-slate-800/50 rounded p-2">
                <span className="text-xs text-slate-400">Échoués</span>
                <Badge className="bg-red-600/20 text-red-400 border-red-600/50">
                  {jobs.failed.length}
                </Badge>
              </div>
            </div>
          </div>
        )}

        {/* Section 3: Actions de Maintenance */}
        <div className="bg-gradient-to-br from-slate-800/50 to-slate-900/50 border border-slate-700 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <Settings className="h-4 w-4 text-orange-400" />
            <h3 className="font-semibold text-sm text-slate-200">Maintenance</h3>
          </div>
          <div className="grid grid-cols-2 gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleMaintenance('clean_logs')}
              disabled={actionLoading !== null}
              className="bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-300 text-xs"
            >
              {actionLoading === 'clean_logs' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3 mr-1" />
              )}
              Nettoyer Logs
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleMaintenance('clean_queue')}
              disabled={actionLoading !== null}
              className="bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-300 text-xs"
            >
              {actionLoading === 'clean_queue' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3 mr-1" />
              )}
              Vider Queue
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleMaintenance('clean_finished_jobs')}
              disabled={actionLoading !== null}
              className="bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-300 text-xs"
            >
              {actionLoading === 'clean_finished_jobs' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Trash2 className="h-3 w-3 mr-1" />
              )}
              Jobs Terminés
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleMaintenance('vacuum_db')}
              disabled={actionLoading !== null}
              className="bg-slate-800 hover:bg-slate-700 border-slate-600 text-slate-300 text-xs"
            >
              {actionLoading === 'vacuum_db' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <Database className="h-3 w-3 mr-1" />
              )}
              Optimiser DB
            </Button>
          </div>
        </div>

        {/* Section 4: Actions de Déploiement */}
        <div className="bg-gradient-to-br from-purple-900/20 to-purple-800/20 border border-purple-600/30 rounded-lg p-4">
          <div className="flex items-center gap-2 mb-3">
            <GitPullRequest className="h-4 w-4 text-purple-400" />
            <h3 className="font-semibold text-sm text-purple-300">Déploiement</h3>
          </div>
          <div className="space-y-2">
            <Button
              size="sm"
              onClick={() => handleDeployment('pull')}
              disabled={actionLoading !== null}
              className="w-full bg-purple-700 hover:bg-purple-600 text-white text-xs"
            >
              {actionLoading === 'pull' ? (
                <Loader2 className="h-3 w-3 animate-spin mr-1" />
              ) : (
                <GitPullRequest className="h-3 w-3 mr-1" />
              )}
              Git Pull (Mise à jour)
            </Button>
            <div className="text-xs text-slate-500 text-center pt-1">
              ⚠️ Les actions rebuild/restart doivent être exécutées depuis l'hôte Docker
            </div>
          </div>
        </div>

        {/* Bouton de rafraîchissement */}
        <Button
          size="sm"
          variant="ghost"
          onClick={async () => {
            setLoading(true)
            await Promise.all([fetchServicesStatus(), fetchJobs()])
            setLoading(false)
          }}
          className="w-full text-slate-400 hover:text-slate-200 text-xs"
        >
          <RefreshCw className="h-3 w-3 mr-1" />
          Rafraîchir les données
        </Button>

      </CardContent>
    </Card>
  )
}
