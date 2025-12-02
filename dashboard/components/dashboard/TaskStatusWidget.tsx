"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Activity, ExternalLink, Terminal } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useState, useEffect } from "react"
import Link from "next/link"
import { getLogs, getBotStatusDetailed } from "@/lib/api"
import { useRouter } from "next/navigation"

export function TaskStatusWidget() {
  const [lastLog, setLastLog] = useState<string>("")
  const [isActive, setIsActive] = useState(false)
  const [lastActiveTime, setLastActiveTime] = useState<string>("")
  const router = useRouter()

  const fetchStatus = async () => {
    try {
      // Get bot status
      const status = await getBotStatusDetailed()
      const running = status.active_jobs.length > 0
      setIsActive(running)

      if (running) {
        setLastActiveTime("En cours...")
      } else {
        // Keeps the last status or specific idle message
      }

      // Get last log line
      const logs = await getLogs(1) // Fetch only 1 line if API supports it, or fetch minimal
      // The current getLogs implementation might fetch all, so we take the last one.
      // Optimization: In a real scenario, we'd want an API endpoint for just the last log.
      // For now, we use existing getLogs.
      if (logs && logs.length > 0) {
        const entry = logs[logs.length - 1]
        setLastLog(`[${entry.level}] ${entry.message}`)
      }
    } catch (error) {
      console.error("Failed to fetch task status", error)
    }
  }

  useEffect(() => {
    fetchStatus()
    const interval = setInterval(fetchStatus, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-slate-400" />
          <CardTitle className="text-sm font-medium text-slate-200">
            Activité en temps réel
          </CardTitle>
        </div>
        <div className="flex items-center gap-2">
            {isActive ? (
                <Badge variant="outline" className="border-emerald-500 text-emerald-500 animate-pulse bg-emerald-500/10">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 mr-2" />
                    En cours
                </Badge>
            ) : (
                <Badge variant="outline" className="text-slate-500 border-slate-700">
                    <span className="w-2 h-2 rounded-full bg-slate-600 mr-2" />
                    En attente
                </Badge>
            )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-4">
            <div className="bg-slate-950 rounded-md p-3 border border-slate-800 font-mono text-xs text-slate-400 truncate min-h-[46px] flex items-center">
                {lastLog ? (
                    <span className="flex items-center gap-2">
                        <Terminal className="h-3 w-3 text-slate-600 flex-shrink-0" />
                        <span className="truncate">{lastLog}</span>
                    </span>
                ) : (
                    <span className="text-slate-600 italic">Aucune activité récente</span>
                )}
            </div>

            <Link href="/logs" className="w-full">
                <Button variant="ghost" className="w-full text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800 h-8">
                    Voir les logs complets
                    <ExternalLink className="ml-2 h-3 w-3" />
                </Button>
            </Link>
        </div>
      </CardContent>
    </Card>
  )
}
