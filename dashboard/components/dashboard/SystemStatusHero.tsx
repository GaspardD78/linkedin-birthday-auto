"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import Link from "next/link"
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  Clock,
  Zap,
  Inbox,
  Cpu,
  HardDrive,
  Cookie,
  Server,
  RefreshCw
} from "lucide-react"
import { getSystemHealth, type SystemHealth } from "@/lib/api"

interface WorkerStatusData {
  status: 'actif' | 'inactif' | 'en attente' | 'inconnu'
  pending_tasks: number
  busy_workers: number
  error?: string
}

interface CookiesStatus {
  valid: boolean
  last_updated: string | null
}

async function fetchWorkerStatus(): Promise<WorkerStatusData> {
  try {
    const response = await fetch('/api/worker/status', { cache: 'no-store' })
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`)
    }
    return await response.json()
  } catch (error) {
    console.error("Failed to fetch worker status:", error)
    return {
      status: 'inconnu',
      pending_tasks: 0,
      busy_workers: 0,
    }
  }
}

async function fetchCookiesStatus(): Promise<CookiesStatus> {
  try {
    const response = await fetch('/api/auth/validate-cookies', { cache: 'no-store' })
    if (!response.ok) {
      return { valid: false, last_updated: new Date().toISOString() }
    }
    return await response.json()
  } catch (error) {
    console.error("Failed to fetch cookies status:", error)
    return { valid: true, last_updated: new Date().toISOString() }
  }
}

export function SystemStatusHero() {
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null)
  const [workerStatus, setWorkerStatus] = useState<WorkerStatusData>({
    status: 'inconnu',
    pending_tasks: 0,
    busy_workers: 0,
  })
  const [cookiesStatus, setCookiesStatus] = useState<CookiesStatus>({
    valid: true,
    last_updated: null
  })
  const [isRefreshing, setIsRefreshing] = useState(false)

  const fetchData = async () => {
    try {
      const [health, worker, cookies] = await Promise.all([
        getSystemHealth(),
        fetchWorkerStatus(),
        fetchCookiesStatus()
      ])
      setSystemHealth(health)
      setWorkerStatus(worker)
      setCookiesStatus(cookies)
    } catch (error) {
      console.error("Failed to fetch status data:", error)
    }
  }

  useEffect(() => {
    fetchData()
    const interval = setInterval(fetchData, 5000) // Refresh every 5 seconds
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = async () => {
    setIsRefreshing(true)
    await fetchData()
    setTimeout(() => setIsRefreshing(false), 500)
  }

  // Calculate global status
  const getGlobalStatus = () => {
    if (!systemHealth) return { status: 'loading', color: 'slate', text: 'Chargement...', icon: Server }

    const cpuCritical = systemHealth.cpu_usage > 80
    const ramCritical = (systemHealth.memory_usage.used / systemHealth.memory_usage.total) > 0.9
    const workerError = workerStatus.status === 'inconnu'
    const cookiesInvalid = !cookiesStatus.valid

    if (cpuCritical || ramCritical || workerError) {
      return { status: 'unhealthy', color: 'red', text: 'Alerte Système', icon: AlertCircle }
    }

    if (cookiesInvalid) {
      return { status: 'degraded', color: 'amber', text: 'Système Dégradé', icon: AlertCircle }
    }

    if (workerStatus.status === 'actif') {
      return { status: 'healthy', color: 'emerald', text: 'Système Opérationnel', icon: CheckCircle2 }
    }

    if (workerStatus.status === 'en attente' && workerStatus.pending_tasks > 0) {
      return { status: 'waiting', color: 'blue', text: 'Tâches en Attente', icon: Clock }
    }

    return { status: 'idle', color: 'slate', text: 'Système en Veille', icon: Activity }
  }

  const globalStatus = getGlobalStatus()
  const memoryUsedGB = systemHealth ? systemHealth.memory_usage.used / (1024 ** 3) : 0
  const memoryTotalGB = systemHealth ? systemHealth.memory_usage.total / (1024 ** 3) : 0
  const memoryPercent = systemHealth ? (memoryUsedGB / memoryTotalGB) * 100 : 0

  return (
    <Card className="bg-slate-900 border-slate-800 shadow-2xl overflow-hidden">
      <CardContent className="p-8">

        {/* Header Section */}
        <div className="flex items-center justify-between mb-8">
          {/* Status Badge & Title */}
          <div className="flex items-center gap-4">
            <div className={`relative h-16 w-16 rounded-full bg-${globalStatus.color}-500/20 border-2 border-${globalStatus.color}-500/50 flex items-center justify-center`}>
              <globalStatus.icon className={`h-8 w-8 text-${globalStatus.color}-500 ${globalStatus.status === 'healthy' || globalStatus.status === 'unhealthy' ? 'animate-pulse' : ''}`} />
              {globalStatus.status === 'healthy' && (
                <div className="absolute -bottom-1 -right-1 h-4 w-4 rounded-full bg-emerald-500 border-2 border-slate-900 animate-pulse" />
              )}
            </div>
            <div>
              <h2 className="text-3xl font-bold text-white mb-1">{globalStatus.text}</h2>
              <p className="text-slate-400 text-sm">LinkedIn Birthday Auto Dashboard v2.0</p>
            </div>
          </div>

          {/* Last Update & Refresh */}
          <div className="text-right flex flex-col items-end gap-2">
            <div>
              <div className="text-xs text-slate-500 mb-1">Dernière mise à jour</div>
              <div className="text-sm text-slate-300 font-mono">
                {new Date().toLocaleTimeString('fr-FR')}
              </div>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
              className="gap-2 border-slate-700 hover:bg-slate-800"
            >
              <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin' : ''}`} />
              Actualiser
            </Button>
          </div>
        </div>

        {/* Metrics Grid */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">

          {/* Workers */}
          <div className="relative bg-gradient-to-br from-emerald-900/30 to-emerald-800/10 border border-emerald-700/40 rounded-xl p-5 overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-emerald-500/10">
            <div className="absolute top-0 right-0 w-20 h-20 bg-emerald-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Zap className="h-4 w-4 text-emerald-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Workers</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-emerald-400">
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

          {/* Queue */}
          <div className="relative bg-gradient-to-br from-blue-900/30 to-blue-800/10 border border-blue-700/40 rounded-xl p-5 overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-blue-500/10">
            <div className="absolute top-0 right-0 w-20 h-20 bg-blue-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Inbox className="h-4 w-4 text-blue-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">Queue</span>
              </div>
              <div className="flex items-end gap-2">
                <span className="text-3xl font-bold text-blue-400">
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

          {/* CPU */}
          <div className="relative bg-gradient-to-br from-purple-900/30 to-purple-800/10 border border-purple-700/40 rounded-xl p-5 overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-purple-500/10">
            <div className="absolute top-0 right-0 w-20 h-20 bg-purple-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <Cpu className="h-4 w-4 text-purple-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">CPU</span>
              </div>
              <div className="flex items-end gap-2">
                <span className={`text-3xl font-bold ${systemHealth && systemHealth.cpu_usage > 70 ? 'text-red-400' : 'text-purple-400'}`}>
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

          {/* RAM */}
          <div className="relative bg-gradient-to-br from-cyan-900/30 to-cyan-800/10 border border-cyan-700/40 rounded-xl p-5 overflow-hidden transition-all duration-300 hover:shadow-lg hover:shadow-cyan-500/10">
            <div className="absolute top-0 right-0 w-20 h-20 bg-cyan-500/10 rounded-full blur-2xl" />
            <div className="relative">
              <div className="flex items-center gap-2 mb-3">
                <HardDrive className="h-4 w-4 text-cyan-400" />
                <span className="text-xs text-slate-400 font-semibold uppercase tracking-wide">RAM</span>
              </div>
              <div className="flex items-end gap-2">
                <span className={`text-3xl font-bold ${memoryPercent > 90 ? 'text-red-400' : 'text-cyan-400'}`}>
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
                      className={`h-full rounded-full transition-all duration-500 ${memoryPercent > 90 ? 'bg-red-500' : 'bg-cyan-500'}`}
                      style={{ width: `${Math.min(memoryPercent, 100)}%` }}
                    />
                  </div>
                </div>
              )}
            </div>
          </div>

        </div>

        {/* Footer Info Bar */}
        <div className="flex items-center justify-between bg-slate-800/50 rounded-lg p-4 border border-slate-700">
          <div className="flex items-center gap-6">
            {/* Worker Status */}
            <div className="flex items-center gap-2">
              <div className={`h-2 w-2 rounded-full ${workerStatus.status === 'actif' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
              <span className="text-xs text-slate-400">
                Workers: <span className="text-slate-200 font-semibold">{workerStatus.status}</span>
              </span>
            </div>

            {/* Cookies Status */}
            <div className="flex items-center gap-2">
              <Cookie className={`h-3 w-3 ${cookiesStatus.valid ? 'text-emerald-500' : 'text-amber-500'}`} />
              <span className="text-xs text-slate-400">
                Cookies: {cookiesStatus.valid ? (
                  <span className="text-emerald-400 font-semibold">Valides</span>
                ) : (
                  <Link href="/auth">
                    <span className="text-amber-400 font-semibold hover:underline cursor-pointer">Expirés ⚠️</span>
                  </Link>
                )}
              </span>
            </div>

            {/* Temperature */}
            {systemHealth && systemHealth.temperature > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-base">🌡️</span>
                <span className="text-xs text-slate-400">
                  Temp: <span className={`font-semibold ${systemHealth.temperature > 70 ? 'text-orange-400' : 'text-slate-200'}`}>
                    {systemHealth.temperature.toFixed(1)}°C
                  </span>
                </span>
              </div>
            )}

            {/* Uptime */}
            {systemHealth && (
              <div className="flex items-center gap-2">
                <Clock className="h-3 w-3 text-slate-500" />
                <span className="text-xs text-slate-400">
                  Uptime: <span className="text-slate-200 font-semibold font-mono">{formatUptime(systemHealth.uptime)}</span>
                </span>
              </div>
            )}
          </div>

          {/* Live Indicator */}
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
  const seconds = parseInt(uptimeStr, 10)
  if (isNaN(seconds)) return "N/A"
  const days = Math.floor(seconds / (3600 * 24))
  const hours = Math.floor((seconds % (3600 * 24)) / 3600)
  const minutes = Math.floor((seconds % 3600) / 60)
  return `${days}d ${hours}h ${minutes}m`
}
