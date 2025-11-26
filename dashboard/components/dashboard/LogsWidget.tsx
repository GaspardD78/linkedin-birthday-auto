"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, RefreshCw } from "lucide-react"
import { Button } from "@/components/ui/button"
import { useState, useEffect, useRef } from "react"
import { getLogs } from "../../lib/api"

export function LogsWidget() {
  const [logs, setLogs] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    logsEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [logs])

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const logEntries = await getLogs()
      const logContent = logEntries.map(log => `[${log.timestamp}] [${log.level}] ${log.message}`).join('\n');
      setLogs(logContent)
    } catch (error) {
      console.error("Failed to fetch logs", error)
      setLogs("❌ Error loading logs... Vérifiez que le bot est démarré.")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
    // Polling toutes les 3 secondes
    const interval = setInterval(fetchLogs, 3000)
    return () => clearInterval(interval)
  }, [])

  return (
    <Card className="bg-slate-900 border-slate-800 h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
          <Terminal className="h-5 w-5 text-emerald-500" />
          🖥️ Console Logs (Temps Réel)
        </CardTitle>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-slate-500 hover:text-emerald-400 hover:bg-slate-800"
          onClick={fetchLogs}
          disabled={loading}
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-emerald-500' : ''}`} />
        </Button>
      </CardHeader>
      <CardContent className="flex-1 min-h-0">
        <div className="bg-slate-950 rounded-md p-4 h-[400px] overflow-y-auto font-mono text-sm text-emerald-500 border border-slate-800 whitespace-pre-wrap shadow-inner">
          {logs || (
            <div className="text-slate-600 italic">
              <span className="text-emerald-500">$</span> Waiting for logs...
              <br />
              <span className="text-slate-700">→ Logs will appear here in real-time (refresh every 3s)</span>
            </div>
          )}
          <div ref={logsEndRef} />
        </div>
        <div className="mt-2 text-xs text-slate-600 flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Auto-refresh: 3s | Auto-scroll: ON
        </div>
      </CardContent>
    </Card>
  )
}
