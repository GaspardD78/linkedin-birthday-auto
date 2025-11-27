"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, HardDrive, Server, Clock, AlertCircle } from "lucide-react"
import { getSystemHealth, type SystemHealth } from "../../lib/api"

export function SystemHealthWidget() {
  const [data, setData] = useState<SystemHealth | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await getSystemHealth()
        setData(health)
        setError(null) // Clear error on success
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Erreur de connexion système"
        console.error("Failed to fetch health stats", error)
        setError(errorMsg)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  // Display error state if health check fails
  if (error) {
    return (
      <Card className="bg-yellow-900/20 border-yellow-600">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-yellow-400 flex items-center gap-2">
            <AlertCircle className="h-4 w-4" />
            Health Check Failed
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-yellow-300">{error}</p>
        </CardContent>
      </Card>
    )
  }

  const formatUptime = (uptimeStr: string) => {
    // Assuming uptime is a string representing seconds.
    const seconds = parseInt(uptimeStr, 10);
    if (isNaN(seconds)) return "N/A";
    const days = Math.floor(seconds / (3600 * 24));
    const hours = Math.floor((seconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  }

  if (!data) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium text-slate-200">
            Hardware Health (RPi 4)
          </CardTitle>
          <Server className="h-4 w-4 text-slate-500" />
        </CardHeader>
        <CardContent>
          <div className="flex justify-center items-center h-24">
            <p className="text-slate-400">Loading...</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const memoryUsedGB = data.memory_usage.used / (1024 ** 3);
  const memoryTotalGB = data.memory_usage.total / (1024 ** 3);

  const memoryPercent = (memoryUsedGB / memoryTotalGB) * 100;

  return (
    <Card className="bg-slate-900 border-slate-800 shadow-xl">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Server className="h-4 w-4 text-slate-400" />
          Santé du Système
        </CardTitle>
        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
      </CardHeader>
      <CardContent>
        <div className="space-y-4">

          {/* CPU Usage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <Cpu className="h-3 w-3" />
                <span>CPU</span>
              </div>
              <span className={`text-sm font-bold ${data.cpu_usage > 70 ? 'text-red-400' : 'text-emerald-400'}`}>
                {Math.round(data.cpu_usage)}%
              </span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className={`h-full transition-all duration-300 ${data.cpu_usage > 70 ? 'bg-red-500' : 'bg-emerald-500'}`}
                style={{ width: `${Math.min(data.cpu_usage, 100)}%` }}
              />
            </div>
          </div>

          {/* RAM Usage */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <HardDrive className="h-3 w-3" />
                <span>RAM</span>
              </div>
              <span className="text-sm font-bold text-blue-400">
                {memoryUsedGB.toFixed(1)} / {memoryTotalGB.toFixed(1)} GB
              </span>
            </div>
            <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 transition-all duration-300"
                style={{ width: `${Math.min(memoryPercent, 100)}%` }}
              />
            </div>
          </div>

          {/* Temperature */}
          {data.temperature > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 text-slate-400 text-xs">
                  <span>🌡️</span>
                  <span>Température</span>
                </div>
                <span className={`text-sm font-bold ${data.temperature > 70 ? 'text-orange-400' : 'text-slate-300'}`}>
                  {data.temperature.toFixed(1)}°C
                </span>
              </div>
            </div>
          )}

          {/* Uptime */}
          <div className="pt-2 border-t border-slate-800">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-slate-400 text-xs">
                <Clock className="h-3 w-3" />
                <span>Uptime</span>
              </div>
              <span className="text-xs font-mono text-slate-200">{formatUptime(data.uptime)}</span>
            </div>
          </div>

        </div>
      </CardContent>
    </Card>
  )
}
