"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Bot,
  Clock,
  Inbox,
  Activity,
  AlertCircle,
  CheckCircle,
  XCircle,
  Pause,
  Play,
  RefreshCw,
  Zap
} from "lucide-react"

// Définition du type pour les données de statut du worker
interface WorkerStatusData {
  status: 'actif' | 'inactif' | 'en attente' | 'inconnu';
  pending_tasks: number;
  busy_workers: number;
  error?: string;
}

interface JobDetails {
  job_id: string
  status: string
  created_at: string
  started_at?: string
}

// Fonction pour récupérer le statut du worker depuis l'API
async function fetchWorkerStatus(): Promise<WorkerStatusData> {
  try {
    const response = await fetch('/api/worker/status', { cache: 'no-store' });
    if (!response.ok) {
      // Gérer les erreurs HTTP
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch worker status:", error);
    // Retourner un état d'erreur clair
    return {
      status: 'inconnu',
      pending_tasks: 0,
      busy_workers: 0,
      error: error instanceof Error ? error.message : "An unknown error occurred",
    };
  }
}

export function BotStatusWidget() {
  const [status, setStatus] = useState<WorkerStatusData>({
    status: 'inconnu',
    pending_tasks: 0,
    busy_workers: 0,
  });
  const [currentJobs, setCurrentJobs] = useState<JobDetails[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<Date>(new Date())

  // Récupérer les jobs en cours
  const fetchCurrentJobs = async () => {
    try {
      const response = await fetch('/api/deployment/jobs')
      if (response.ok) {
        const data = await response.json()
        setCurrentJobs(data.started || [])
      }
    } catch (error) {
      console.error("Failed to fetch current jobs:", error)
    }
  }

  // Hook pour rafraîchir les données toutes les 5 secondes
  useEffect(() => {
    const fetchData = async () => {
      const data = await fetchWorkerStatus();
      setStatus(data);
      await fetchCurrentJobs()
      setLastUpdate(new Date())
    };

    fetchData(); // Appel initial
    const interval = setInterval(fetchData, 5000); // Rafraîchir toutes les 5 secondes

    return () => clearInterval(interval); // Nettoyage de l'intervalle
  }, []);

  const handleRefresh = async () => {
    setLoading(true)
    const data = await fetchWorkerStatus();
    setStatus(data);
    await fetchCurrentJobs()
    setLastUpdate(new Date())
    setLoading(false)
  }

  // Fonction pour déterminer la couleur en fonction du statut
  const getStatusColor = (state: string) => {
    switch (state) {
      case 'actif': return 'text-blue-500';
      case 'en attente': return 'text-orange-500';
      case 'inactif': return 'text-slate-500';
      default: return 'text-red-500'; // 'inconnu' ou erreur
    }
  };

  const getStatusIcon = (state: string) => {
    switch (state) {
      case 'actif': return <Activity className="h-5 w-5 text-blue-500 animate-pulse" />;
      case 'en attente': return <Clock className="h-5 w-5 text-orange-500" />;
      case 'inactif': return <Pause className="h-5 w-5 text-slate-500" />;
      default: return <AlertCircle className="h-5 w-5 text-red-500" />;
    }
  };

  const getStatusBadge = (state: string) => {
    switch (state) {
      case 'actif': return <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/50">🔵 Actif</Badge>;
      case 'en attente': return <Badge className="bg-orange-600/20 text-orange-400 border-orange-600/50">🟠 En attente</Badge>;
      case 'inactif': return <Badge className="bg-slate-600/20 text-slate-400 border-slate-600/50">⚪ Inactif</Badge>;
      default: return <Badge className="bg-red-600/20 text-red-400 border-red-600/50">🔴 Inconnu</Badge>;
    }
  };

  const statusText = status.status.charAt(0).toUpperCase() + status.status.slice(1);
  const formatTime = (date: Date) => {
    return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-3">
        <div className="flex items-center gap-2">
          {getStatusIcon(status.status)}
          <CardTitle className="text-base font-semibold text-slate-200">
            État des Workers
          </CardTitle>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-slate-500 hover:text-blue-400"
          onClick={handleRefresh}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent>
        <div className="space-y-4">
          {/* Statut principal avec badge */}
          <div className="flex items-center justify-between">
            {getStatusBadge(status.status)}
            <span className="text-xs text-slate-500">
              Mis à jour: {formatTime(lastUpdate)}
            </span>
          </div>

          {/* Métriques en grille */}
          <div className="grid grid-cols-2 gap-3">
            {/* Tâches en attente */}
            <div className="bg-gradient-to-br from-blue-900/20 to-blue-800/10 border border-blue-700/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Inbox className="h-4 w-4 text-blue-400" />
                <span className="text-xs text-slate-400">Queue</span>
              </div>
              <div className="text-2xl font-bold text-blue-400">
                {status.pending_tasks}
              </div>
              <div className="text-xs text-slate-500">
                {status.pending_tasks === 0 ? 'Aucune tâche' : status.pending_tasks === 1 ? 'tâche' : 'tâches'}
              </div>
            </div>

            {/* Workers actifs */}
            <div className="bg-gradient-to-br from-emerald-900/20 to-emerald-800/10 border border-emerald-700/30 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-1">
                <Zap className="h-4 w-4 text-emerald-400" />
                <span className="text-xs text-slate-400">Workers</span>
              </div>
              <div className="text-2xl font-bold text-emerald-400">
                {status.busy_workers}
              </div>
              <div className="text-xs text-slate-500">
                {status.busy_workers === 0 ? 'Inactif' : status.busy_workers === 1 ? 'actif' : 'actifs'}
              </div>
            </div>
          </div>

          {/* Jobs en cours */}
          {currentJobs.length > 0 && (
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-3">
              <div className="flex items-center gap-2 mb-2">
                <Activity className="h-3 w-3 text-amber-400" />
                <span className="text-xs font-semibold text-slate-300">Job en cours</span>
              </div>
              {currentJobs.map((job) => (
                <div key={job.job_id} className="text-xs text-slate-400 space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[10px] font-mono text-slate-500 truncate">
                      ID: {job.job_id.slice(0, 8)}...
                    </span>
                  </div>
                  {job.started_at && (
                    <div className="text-[10px] text-slate-500">
                      Démarré: {new Date(job.started_at).toLocaleTimeString('fr-FR')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Indicateur visuel de l'état */}
          <div className="flex items-center justify-center gap-2 pt-2 border-t border-slate-800">
            {status.status === 'actif' && (
              <div className="flex items-center gap-2 text-xs text-blue-400">
                <div className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                <span>Traitement en cours...</span>
              </div>
            )}
            {status.status === 'en attente' && (
              <div className="flex items-center gap-2 text-xs text-orange-400">
                <Clock className="h-3 w-3" />
                <span>En attente de tâches</span>
              </div>
            )}
            {status.status === 'inactif' && (
              <div className="flex items-center gap-2 text-xs text-slate-500">
                <Pause className="h-3 w-3" />
                <span>Worker inactif</span>
              </div>
            )}
            {status.status === 'inconnu' && status.error && (
              <div className="flex items-center gap-2 text-xs text-red-400">
                <AlertCircle className="h-3 w-3" />
                <span className="truncate">{status.error}</span>
              </div>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
