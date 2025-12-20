"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent } from "@/components/ui/card"
import {
  Activity,
  Cpu,
  HardDrive,
  Zap,
  Inbox,
  Server,
  AlertCircle,
  CheckCircle2,
  Clock
} from "lucide-react"
import { getSystemHealth, type SystemHealth } from "../../lib/api"

interface WorkerStatusData {
  status: 'actif' | 'inactif' | 'en attente' | 'inconnu';
  pending_tasks: number;
  busy_workers: number;
  error?: string;
}

async function fetchWorkerStatus(): Promise<WorkerStatusData> {
  try {
    const response = await fetch('/api/worker/status', { cache: 'no-store' });
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    return {
      status: 'inconnu',
      pending_tasks: 0,
      busy_workers: 0,
      error: error instanceof Error ? error.message : "An unknown error occurred",
    };
  }
}

export function PilotageOverview() {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [workerStatus, setWorkerStatus] = useState<WorkerStatusData>({
    status: 'inconnu',
    pending_tasks: 0,
    busy_workers: 0,
  })

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [health, worker] = await Promise.all([
          getSystemHealth(),
          fetchWorkerStatus()
        ])
        setSystemHealth(health)
        setWorkerStatus(worker)
      } catch (error) {
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds

    return () => clearInterval(interval)
  }, [])

  const getGlobalStatus = () => {
    if (!systemHealth) return { status: 'inconnu', color: 'slate', text: 'Chargement...' }

    const cpuCritical = systemHealth.cpu_usage > 80
    const ramCritical = (systemHealth.memory_usage.used / systemHealth.memory_usage.total) > 0.9
    const workerError = workerStatus.status === 'inconnu'

    if (cpuCritical || ramCritical || workerError) {
      return { status: 'alerte', color: 'red', text: 'Alerte Système' }
    }

    if (workerStatus.status === 'actif') {
      return { status: 'operationnel', color: 'emerald', text: 'Système Opérationnel' }
    }

    if (workerStatus.status === 'en attente' && workerStatus.pending_tasks > 0) {
      return { status: 'attente', color: 'amber', text: 'Tâches en Attente' }
    }

    return { status: 'idle', color: 'blue', text: 'Système en Veille' }
  }

  const globalStatus = getGlobalStatus()
  const memoryUsedGB = systemHealth ? systemHealth.memory_usage.used / (1024 ** 3) : 0
  const memoryTotalGB = systemHealth ? systemHealth.memory_usage.total / (1024 ** 3) : 0

  return (
    <Card className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border-slate-700 shadow-2xl overflow-hidden">
      <CardContent className="p-8">

        {/* Header with Global Status */}
        <div className="flex items-center justify-between mb-8">
          <div className="flex items-center gap-4">
            <div className={`relative h-16 w-16 rounded-full bg-gradient-to-br from-${globalStatus.color}-500 to-${globalStatus.color}-700 flex items-center justify-center shadow-lg shadow-${globalStatus.color}-500/50`}>
              {globalStatus.status === 'operationnel' && <CheckCircle2 className="h-8 w-8 text-white" />}
              {globalStatus.status === 'alerte' && <AlertCircle className="h-8 w-8 text-white animate-pulse" />}
              {globalStatus.status === 'attente' && <Clock className="h-8 w-8 text-white" />}
              {globalStatus.status === 'idle' && <Activity className="h-8 w-8 text-white" />}
              {globalStatus.status === 'inconnu' && <Server className="h-8 w-8 text-white" />}
              <div className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full bg-emerald-500 border-2 border-slate-900 animate-pulse" />
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-1">{globalStatus.text}</h2>
              <p className="text-slate-400 text-sm">Centre de Pilotage LinkedIn Bot</p>
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-slate-500 mb-1">Dernière mise à jour</div>
            <div className="text-sm text-slate-300 font-mono">
              {new Date().toLocaleTimeString('fr-FR')}
            </div>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">

          {/* Workers Actifs */}
          <div className="relative bg-gradient-to-br from-emerald-900/40 to-emerald-800/20 border border-emerald-700/50 rounded-xl p-5 overflow-hidden">
            <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="h-5 w-5 text-emerald-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Workers</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-bold text-emerald-400">
                  {workerStatus.busy_workers}
                </span>
                <span className="text-slate-500 text-sm mb-1">
                  {workerStatus.busy_workers === 0 ? 'inactif' : workerStatus.busy_workers === 1 ? 'actif' : 'actifs'}
                </span>
              </div>
              {workerStatus.busy_workers > 0 && (
                <div className="mt-2 flex items-center gap-1">
                  <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                  <span className="text-xs text-emerald-400">En traitement</span>
                </div>
              )}
            </div>
          </div>

          {/* Tâches en Attente */}
          <div className="relative bg-gradient-to-br from-blue-900/40 to-blue-800/20 border border-blue-700/50 rounded-xl p-5 overflow-hidden">
            <div className="absolute top-0 right-0 w-20 h-20 bg-blue-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Inbox className="h-5 w-5 text-blue-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Queue</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-bold text-blue-400">
                  {workerStatus.pending_tasks}
                </span>
                <span className="text-slate-500 text-sm mb-1">
                  {workerStatus.pending_tasks === 0 ? 'vide' : workerStatus.pending_tasks === 1 ? 'tâche' : 'tâches'}
                </span>
              </div>
              {workerStatus.pending_tasks > 0 && (
                <div className="mt-2">
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div className="h-full bg-blue-500 rounded-full animate-pulse" style={{ width: '60%' }} />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* CPU Usage */}
          <div className="relative bg-gradient-to-br from-purple-900/40 to-purple-800/20 border border-purple-700/50 rounded-xl p-5 overflow-hidden">
            <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Cpu className="h-5 w-5 text-purple-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">CPU</span>
              </div>
              <div className="flex items-end gap-2">
                <span className={`text-4xl font-bold ${systemHealth && systemHealth.cpu_usage > 70 ? 'text-red-400' : 'text-purple-400'}`}>
                  {systemHealth ? Math.round(systemHealth.cpu_usage) : '--'}
                </span>
                <span className="text-slate-500 text-sm mb-1">%</span>
              </div>
              {systemHealth && (
                <div className="mt-2">
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${systemHealth.cpu_usage > 70 ? 'bg-red-500' : 'bg-purple-500'}`}
                      style={{ width: `${Math.min(systemHealth.cpu_usage, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* RAM Usage */}
          <div className="relative bg-gradient-to-br from-cyan-900/40 to-cyan-800/20 border border-cyan-700/50 rounded-xl p-5 overflow-hidden">
            <div className="absolute top-0 right-0 w-20 h-20 bg-cyan-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <HardDrive className="h-5 w-5 text-cyan-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">RAM</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-4xl font-bold text-cyan-400">
                  {systemHealth ? memoryUsedGB.toFixed(1) : '--'}
                </span>
                <span className="text-slate-500 text-sm mb-1">
                  / {systemHealth ? memoryTotalGB.toFixed(1) : '--'} GB
                </span>
              </div>
              {systemHealth && (
                <div className="mt-2">
                  <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-cyan-500 rounded-full transition-all duration-500"
                      style={{ width: `${Math.min((memoryUsedGB / memoryTotalGB) * 100, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Status Indicators */}
        <div className="mt-6 flex items-center justify-between bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full ${workerStatus.status === 'actif' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
              <span className="text-xs text-slate-400">
                Workers: <span className="text-slate-200 font-semibold">{workerStatus.status}</span>
              </span>
            </div>
            {systemHealth && systemHealth.temperature > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-lg">🌡️</span>
                <span className="text-xs text-slate-400">
                  Temp: <span className={`font-semibold ${systemHealth.temperature > 70 ? 'text-orange-400' : 'text-slate-200'}`}>
                    {systemHealth.temperature.toFixed(1)}°C
                  </span>
                </span>
              </div>
            )}
            {systemHealth && (
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3 text-slate-500" />
                <span className="text-xs text-slate-400">
                  Uptime: <span className="text-slate-200 font-semibold font-mono">{formatUptime(systemHealth.uptime)}</span>
                </span>
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-slate-400">Mise à jour en temps réel</span>
          </div>
        </div>

      </CardContent>
    </Card>
  )
}

function formatUptime(uptimeStr: string): string {
  const seconds = parseInt(uptimeStr, 10);
  if (isNaN(seconds)) return "N/A";
  const days = Math.floor(seconds / (3600 * 24));
  const hours = Math.floor((seconds % (3600 * 24)) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  return `${days}d ${hours}h ${minutes}m`;
}
