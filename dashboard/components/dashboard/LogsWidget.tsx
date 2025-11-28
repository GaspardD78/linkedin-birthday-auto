"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, RefreshCw, Plug } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useState, useEffect, useRef } from "react"
import { getLogs } from "../../lib/api"

export function LogsWidget() {
  const [logs, setLogs] = useState<string>("")
  const [loading, setLoading] = useState(false)
  const [logsConnected, setLogsConnected] = useState<boolean | null>(null)
  const logsContainerRef = useRef<HTMLDivElement>(null)

  // Auto-scroll to bottom of logs container only (not entire page)
  const scrollToBottom = () => {
    if (logsContainerRef.current) {
      logsContainerRef.current.scrollTop = logsContainerRef.current.scrollHeight
    }
  }

  useEffect(() => {
    scrollToBottom()
  }, [logs])

  const checkLogsStatus = async () => {
    try {
      const response = await fetch('/api/logs/status')
      const data = await response.json()
      setLogsConnected(data.connected)
    } catch (error) {
      console.error("Failed to check logs status", error)
      setLogsConnected(false)
    }
  }

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
    checkLogsStatus()
    fetchLogs()
    // Polling toutes les 3 secondes
    const interval = setInterval(fetchLogs, 3000)
    // Vérifier le statut toutes les 30 secondes
    const statusInterval = setInterval(checkLogsStatus, 30000)
    return () => {
      clearInterval(interval)
      clearInterval(statusInterval)
    }
  }, [])

  return (
    <Card className="bg-slate-900 border-slate-800 h-full flex flex-col">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-3">
          <Terminal className="h-5 w-5 text-emerald-500" />
          <CardTitle className="text-lg font-semibold text-slate-200">
            🖥️ Console Logs (Temps Réel)
          </CardTitle>
          {logsConnected !== null && (
            <Badge
              variant={logsConnected ? "default" : "destructive"}
              className={logsConnected ? "bg-emerald-600 text-white" : ""}
            >
              <Plug className="h-3 w-3 mr-1" />
              {logsConnected ? "Connecté" : "Déconnecté"}
            </Badge>
          )}
        </div>
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
        <div
          ref={logsContainerRef}
          className="rounded-md p-4 h-[400px] overflow-y-auto font-mono text-sm border whitespace-pre-wrap shadow-inner custom-scrollbar"
          style={{
            backgroundColor: '#1e1e1e',
            borderColor: '#333333',
            color: '#d4d4d4'
          }}
        >
          {logs ? (
            <div className="space-y-0.5">
              {logs.split('\n').map((line, index) => {
                // Color-code based on log level
                let lineColor = '#d4d4d4' // Default
                if (line.includes('[ERROR]')) lineColor = '#f87171' // Red
                else if (line.includes('[WARNING]') || line.includes('[WARN]')) lineColor = '#fbbf24' // Yellow
                else if (line.includes('[INFO]')) lineColor = '#60a5fa' // Blue
                else if (line.includes('[SUCCESS]')) lineColor = '#4ade80' // Green
                else if (line.includes('[DEBUG]')) lineColor = '#a78bfa' // Purple

                return (
                  <div key={index} style={{ color: lineColor }}>
                    {line}
                  </div>
                )
              })}
            </div>
          ) : (
            <div className="text-slate-500 italic">
              <span className="text-emerald-400">$</span> Waiting for logs...
              <br />
              <span className="text-slate-600">→ Logs will appear here in real-time (refresh every 3s)</span>
            </div>
          )}
        </div>
        <div className="mt-2 text-xs text-slate-600 flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          Auto-refresh: 3s | Auto-scroll: ON
        </div>
      </CardContent>
    </Card>
  )
}
