"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cpu, HardDrive, Server } from "lucide-react"

interface SystemHealthData {
  cpuTemp: number;
  memoryUsage: number;
  diskSpace?: number;
}

export function SystemHealthWidget() {
  // État simulé pour le moment, à connecter avec l'API plus tard
  const [data, setData] = useState<SystemHealthData>({
    cpuTemp: 45,
    memoryUsage: 1.2, // GB
  })

  // Simulation de mise à jour
  useEffect(() => {
    const interval = setInterval(() => {
      // En production, fetch('/api/system/health') ici
      setData(prev => ({
        cpuTemp: 40 + Math.random() * 15,
        memoryUsage: 0.8 + Math.random() * 0.5,
      }))
    }, 3000)
    return () => clearInterval(interval)
  }, [])

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
            <p className="text-[10px] text-slate-500">/ 4.0 GB Total</p>
          </div>

        </div>
      </CardContent>
    </Card>
  )
}
