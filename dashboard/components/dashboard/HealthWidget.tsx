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

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200">
          Hardware Health (RPi 4)
        </CardTitle>
        <Server className="h-4 w-4 text-slate-500" />
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-4 mt-2">

          {/* CPU Temp */}
          <div className="flex flex-col">
            <div className="flex items-center text-slate-400 mb-1 text-xs">
              <Cpu className="mr-2 h-3 w-3" />
              CPU Usage
            </div>
            <div className={`text-2xl font-bold ${data.cpu_usage > 70 ? 'text-red-500' : 'text-emerald-500'}`}>
              {Math.round(data.cpu_usage)}%
            </div>
          </div>

          {/* RAM Usage */}
          <div className="flex flex-col">
            <div className="flex items-center text-slate-400 mb-1 text-xs">
              <HardDrive className="mr-2 h-3 w-3" />
              RAM Usage
            </div>
            <div className="text-2xl font-bold text-blue-500">
              {memoryUsedGB.toFixed(1)} GB
            </div>
            <p className="text-[10px] text-slate-500">
              / {memoryTotalGB.toFixed(1)} GB Total
            </p>
          </div>

          {/* Uptime (Full width) */}
          <div className="col-span-2 flex items-center gap-2 pt-2 border-t border-slate-800">
             <Clock className="h-3 w-3 text-slate-500" />
             <span className="text-xs text-slate-400">Uptime:</span>
             <span className="text-xs font-mono text-slate-200">{formatUptime(data.uptime)}</span>
          </div>

        </div>
      </CardContent>
    </Card>
  )
}
