"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useEffect } from "react"
import { api } from "@/lib/api"

export function LogsWidget() {
  const [logs, setLogs] = useState<string>("")
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const content = await api.getLogs()
      setLogs(content)
    } catch (error) {
      console.error("Failed to fetch logs", error)
      setLogs("Error loading logs...")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    // Refresh every 10 seconds
    const interval = setInterval(fetchLogs, 10000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="bg-slate-900 border-slate-800 h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Terminal className="h-4 w-4" />
          System Logs
        </CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 text-slate-500 hover:text-white"
          onClick={fetchLogs}
          disabled={loading}
        >
          <RefreshCw className={`h-3 w-3 ${loading ? 'animate-spin' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <div className="bg-slate-950 rounded-md p-4 h-[300px] overflow-y-auto font-mono text-xs text-slate-300 border border-slate-800 whitespace-pre-wrap">
          {logs || "No logs available."}
        </div>
      </CardContent>
    </Card>
  )
}
