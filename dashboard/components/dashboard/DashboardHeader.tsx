"use client"

import { useState, useEffect } from 'react'
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  Activity,
  Server,
  CheckCircle,
  AlertCircle,
  XCircle,
  Clock,
  TrendingUp
} from "lucide-react"

interface HealthStatus {
  overall: 'healthy' | 'degraded' | 'unhealthy'
  api: boolean
  worker: boolean
  redis: boolean
  database: boolean
}

export function DashboardHeader() {
  const [health, setHealth] = useState<HealthStatus>({
    overall: 'healthy',
    api: true,
    worker: true,
    redis: true,
    database: true
  })
  const [workerStatus, setWorkerStatus] = useState({
    status: 'inactif',
    pending_tasks: 0,
    busy_workers: 0
  })

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const res = await fetch('/api/system/health')
        if (res.ok) {
          const data = await res.json()
          setHealth({
            overall: data.overall_status || 'healthy',
            api: data.api_healthy || true,
            worker: data.worker_healthy || true,
            redis: data.redis_healthy || true,
            database: data.database_healthy || true
          })
        }
      } catch (error) {
        console.error('Failed to fetch health:', error)
      }
    }

    const fetchWorkerStatus = async () => {
      try {
        const res = await fetch('/api/worker/status')
        if (res.ok) {
          const data = await res.json()
          setWorkerStatus(data)
        }
      } catch (error) {
        console.error('Failed to fetch worker status:', error)
      }
    }

    fetchHealth()
    fetchWorkerStatus()

    const interval = setInterval(() => {
      fetchHealth()
      fetchWorkerStatus()
    }, 10000)

    return () => clearInterval(interval)
  }, [])

  const getOverallStatusIcon = () => {
    switch (health.overall) {
      case 'healthy':
        return <CheckCircle className="h-5 w-5 text-emerald-500" />
      case 'degraded':
        return <AlertCircle className="h-5 w-5 text-orange-500" />
      case 'unhealthy':
        return <XCircle className="h-5 w-5 text-red-500" />
      default:
        return <Activity className="h-5 w-5 text-slate-500" />
    }
  }

  const getOverallStatusBadge = () => {
    switch (health.overall) {
      case 'healthy':
        return (
          <Badge className="bg-emerald-600/20 text-emerald-400 border-emerald-600/50 flex items-center gap-1">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Système opérationnel
          </Badge>
        )
      case 'degraded':
        return (
          <Badge className="bg-orange-600/20 text-orange-400 border-orange-600/50 flex items-center gap-1">
            <div className="h-2 w-2 rounded-full bg-orange-500 animate-pulse" />
            Dégradé
          </Badge>
        )
      case 'unhealthy':
        return (
          <Badge className="bg-red-600/20 text-red-400 border-red-600/50 flex items-center gap-1">
            <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
            Problème détecté
          </Badge>
        )
    }
  }

  const getWorkerStatusBadge = () => {
    const { status, pending_tasks, busy_workers } = workerStatus

    if (status === 'actif' && busy_workers > 0) {
      return (
        <Badge className="bg-blue-600/20 text-blue-400 border-blue-600/50 flex items-center gap-1">
          <Activity className="h-3 w-3 animate-pulse" />
          {busy_workers} worker{busy_workers > 1 ? 's' : ''} actif{busy_workers > 1 ? 's' : ''}
        </Badge>
      )
    } else if (pending_tasks > 0) {
      return (
        <Badge className="bg-orange-600/20 text-orange-400 border-orange-600/50 flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {pending_tasks} tâche{pending_tasks > 1 ? 's' : ''} en attente
        </Badge>
      )
    } else {
      return (
        <Badge className="bg-slate-600/20 text-slate-400 border-slate-600/50 flex items-center gap-1">
          <Activity className="h-3 w-3" />
          En veille
        </Badge>
      )
    }
  }

  return (
    <div className="bg-gradient-to-r from-slate-900/50 via-slate-900/30 to-slate-900/50 border-b border-slate-800 rounded-lg p-6 mb-6 backdrop-blur-sm">
      {/* Main Header */}
      <div className="flex flex-col lg:flex-row lg:justify-between lg:items-start gap-4 mb-4">
        {/* Title Section */}
        <div>
          <div className="flex items-center gap-3 mb-2">
            <h1 className="text-3xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent tracking-tight">
              LinkedIn Birthday Auto
            </h1>
            <span className="text-xs text-slate-500 font-mono px-2 py-1 bg-slate-800/50 rounded">
              v2.0.0
            </span>
          </div>
          <p className="text-slate-400 text-sm">
            Console de pilotage et monitoring en temps réel
          </p>
        </div>

        {/* Status Indicators */}
        <div className="flex flex-col lg:items-end gap-3">
          {getOverallStatusBadge()}
          {getWorkerStatusBadge()}
        </div>
      </div>

      {/* Quick Stats Bar */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 pt-4 border-t border-slate-800/50">
        {/* API Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 rounded-lg">
          <Server className={`h-4 w-4 ${health.api ? 'text-emerald-500' : 'text-red-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">API</div>
            <div className="text-xs font-semibold text-white truncate">
              {health.api ? 'Online' : 'Offline'}
            </div>
          </div>
        </div>

        {/* Worker Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 rounded-lg">
          <Activity className={`h-4 w-4 ${health.worker ? 'text-emerald-500' : 'text-red-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">Worker</div>
            <div className="text-xs font-semibold text-white truncate">
              {health.worker ? 'Ready' : 'Stopped'}
            </div>
          </div>
        </div>

        {/* Redis Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 rounded-lg">
          <Server className={`h-4 w-4 ${health.redis ? 'text-emerald-500' : 'text-red-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">Redis</div>
            <div className="text-xs font-semibold text-white truncate">
              {health.redis ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>

        {/* Database Status */}
        <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/30 rounded-lg">
          <Server className={`h-4 w-4 ${health.database ? 'text-emerald-500' : 'text-red-500'}`} />
          <div className="flex-1 min-w-0">
            <div className="text-xs text-slate-500">Database</div>
            <div className="text-xs font-semibold text-white truncate">
              {health.database ? 'Connected' : 'Disconnected'}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
