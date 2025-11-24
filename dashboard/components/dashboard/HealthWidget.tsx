"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, HardDrive, Server, Clock } from "lucide-react"
import { api, type SystemHealth } from "@/lib/api"

export function SystemHealthWidget() {
  const [data, setData] = useState<SystemHealth>({
    cpuTemp: 0,
    memoryUsage: 0,
    totalMemory: 0,
    uptime: 0
  })

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const health = await api.getHealth()
        setData(health)
      } catch (error) {
        console.error("Failed to fetch health stats", error)
      }
    }

    fetchHealth()
    const interval = setInterval(fetchHealth, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / (3600 * 24));
    const hours = Math.floor((seconds % (3600 * 24)) / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    return `${days}d ${hours}h ${minutes}m`;
  }

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
              CPU Temp
            </div>
            <div className={`text-2xl font-bold ${data.cpuTemp > 70 ? 'text-red-500' : 'text-emerald-500'}`}>
              {Math.round(data.cpuTemp)}°C
            </div>
          </div>

          {/* RAM Usage */}
          <div className="flex flex-col">
            <div className="flex items-center text-slate-400 mb-1 text-xs">
              <HardDrive className="mr-2 h-3 w-3" />
              RAM Usage
            </div>
            <div className="text-2xl font-bold text-blue-500">
              {data.memoryUsage.toFixed(1)} GB
            </div>
            <p className="text-[10px] text-slate-500">
              / {data.totalMemory ? data.totalMemory.toFixed(1) : '4.0'} GB Total
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
