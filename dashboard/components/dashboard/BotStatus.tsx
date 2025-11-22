"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, Activity, AlertCircle } from "lucide-react"

interface BotStatusData {
  state: 'IDLE' | 'WORKING' | 'COOLDOWN' | 'ERROR' | 'STARTING' | 'STOPPING';
  currentTask?: string;
  lastActive: number;
}

export function BotStatusWidget() {
  const [status, setStatus] = useState<BotStatusData>({
    state: 'IDLE',
    lastActive: Date.now()
  })

  const getStatusColor = (state: string) => {
    switch (state) {
      case 'WORKING': return 'text-blue-500';
      case 'COOLDOWN': return 'text-orange-500';
      case 'ERROR': return 'text-red-500';
      case 'IDLE': return 'text-slate-500';
      case 'STARTING': return 'text-emerald-500';
      default: return 'text-slate-500';
    }
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200">
          Bot Status
        </CardTitle>
        <Bot className={`h-4 w-4 ${getStatusColor(status.state)}`} />
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-2">
          <div className="flex items-center gap-2">
            <div className={`h-2.5 w-2.5 rounded-full bg-current ${getStatusColor(status.state)}`} />
            <span className="text-2xl font-bold text-white">{status.state}</span>
          </div>

          {status.currentTask && (
            <div className="text-xs text-slate-400 flex items-center gap-1">
              <Activity className="h-3 w-3" />
              {status.currentTask}
            </div>
          )}

          <div className="text-xs text-slate-500 mt-1">
            Last active: {new Date(status.lastActive).toLocaleTimeString()}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
