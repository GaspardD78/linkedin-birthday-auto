"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal, RefreshCw, Plug, Download, Copy, Filter, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { useState, useEffect, useRef } from "react"
import { getLogs } from "../../lib/api"

type LogLevel = 'ALL' | 'ERROR' | 'WARNING' | 'INFO' | 'SUCCESS' | 'DEBUG'

interface ParsedLog {
  timestamp: string
  level: string
  message: string
  rawLine: string
}

export function LogsWidget() {
  const [logs, setLogs] = useState<string>("")
  const [parsedLogs, setParsedLogs] = useState<ParsedLog[]>([])
  const [loading, setLoading] = useState(false)
  const [logsConnected, setLogsConnected] = useState<boolean | null>(null)
  const [filterLevel, setFilterLevel] = useState<LogLevel>('ALL')
  const [showFilters, setShowFilters] = useState(false)
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
      setLogsConnected(false)
    }
  }

  const parseLogLine = (line: string): ParsedLog => {
    // Regex pour extraire: [timestamp] [level] message
    const match = line.match(/\[([\d\-\s:]+)\]\s*\[(\w+)\]\s*(.+)/)
    if (match) {
      return {
        timestamp: match[1].trim(),
        level: match[2].toUpperCase(),
        message: match[3].trim(),
        rawLine: line
      }
    }
    // Si pas de match, retourner une ligne simple
    return {
      timestamp: '',
      level: 'INFO',
      message: line,
      rawLine: line
    }
  }

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const logEntries = await getLogs()
      const logContent = logEntries.map(log => `[${log.timestamp}] [${log.level}] ${log.message}`).join('\n');
      setLogs(logContent)

      // Parser les logs
      const parsed = logContent.split('\n')
        .filter(line => line.trim())
        .map(parseLogLine)
      setParsedLogs(parsed)
    } catch (error) {
      setLogs("❌ Error loading logs... Vérifiez que le bot est démarré.")
      setParsedLogs([])
    } finally {
      setLoading(false)
    }
  }

  const copyLogs = () => {
    navigator.clipboard.writeText(logs)
    alert('✅ Logs copiés dans le presse-papier')
  }

  const downloadLogs = () => {
    const blob = new Blob([logs], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `linkedin-bot-logs-${new Date().toISOString()}.txt`
    a.click()
    URL.revokeObjectURL(url)
  }

  const getFilteredLogs = (): ParsedLog[] => {
    if (filterLevel === 'ALL') return parsedLogs
    return parsedLogs.filter(log => log.level === filterLevel)
  }

  const getLevelColor = (level: string): string => {
    switch (level) {
      case 'ERROR': return '#f87171' // Red
      case 'WARNING': case 'WARN': return '#fbbf24' // Yellow
      case 'INFO': return '#60a5fa' // Blue
      case 'SUCCESS': return '#4ade80' // Green
      case 'DEBUG': return '#a78bfa' // Purple
      default: return '#d4d4d4' // Default
    }
  }

  const getLevelIcon = (level: string): string => {
    switch (level) {
      case 'ERROR': return '❌'
      case 'WARNING': case 'WARN': return '⚠️'
      case 'INFO': return 'ℹ️'
      case 'SUCCESS': return '✅'
      case 'DEBUG': return '🔍'
      default: return '📝'
    }
  }

  const getLevelStats = () => {
    const stats = {
      ERROR: 0,
      WARNING: 0,
      INFO: 0,
      SUCCESS: 0,
      DEBUG: 0
    }
    parsedLogs.forEach(log => {
      const level = log.level === 'WARN' ? 'WARNING' : log.level
      if (level in stats) {
        stats[level as keyof typeof stats]++
      }
    })
    return stats
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

  const stats = getLevelStats()
  const filteredLogs = getFilteredLogs()

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
          <Badge className="bg-slate-700 text-slate-200">
            {filteredLogs.length} lignes
          </Badge>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-500 hover:text-blue-400 hover:bg-slate-800"
            onClick={() => setShowFilters(!showFilters)}
            title="Filtres"
          >
            <Filter className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-500 hover:text-blue-400 hover:bg-slate-800"
            onClick={copyLogs}
            title="Copier"
          >
            <Copy className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-500 hover:text-blue-400 hover:bg-slate-800"
            onClick={downloadLogs}
            title="Télécharger"
          >
            <Download className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-8 w-8 text-slate-500 hover:text-emerald-400 hover:bg-slate-800"
            onClick={fetchLogs}
            disabled={loading}
            title="Rafraîchir"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin text-emerald-500' : ''}`} />
          </Button>
        </div>
      </CardHeader>

      {/* Filtres et Statistiques */}
      {showFilters && (
        <div className="px-4 pb-3 space-y-3">
          {/* Statistiques par niveau */}
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setFilterLevel('ALL')}
              className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                filterLevel === 'ALL'
                  ? 'bg-slate-700 text-white'
                  : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
              }`}
            >
              Tout ({parsedLogs.length})
            </button>
            {(['ERROR', 'WARNING', 'INFO', 'SUCCESS', 'DEBUG'] as const).map(level => (
              <button
                key={level}
                onClick={() => setFilterLevel(level)}
                className={`px-3 py-1 rounded text-xs font-medium transition-all ${
                  filterLevel === level
                    ? 'ring-2 ring-offset-2 ring-offset-slate-900'
                    : 'hover:opacity-80'
                }`}
                style={{
                  backgroundColor: filterLevel === level ? getLevelColor(level) : `${getLevelColor(level)}33`,
                  color: filterLevel === level ? '#fff' : getLevelColor(level)
                }}
              >
                {getLevelIcon(level)} {level} ({stats[level]})
              </button>
            ))}
          </div>
        </div>
      )}
      <CardContent className="flex-1 min-h-0">
        <div
          ref={logsContainerRef}
          className="rounded-md p-3 h-[400px] overflow-y-auto font-mono text-xs border shadow-inner custom-scrollbar"
          style={{
            backgroundColor: '#1e1e1e',
            borderColor: '#333333',
            color: '#d4d4d4'
          }}
        >
          {filteredLogs.length > 0 ? (
            <div className="space-y-1">
              {filteredLogs.map((log, index) => (
                <div
                  key={`log-${log.timestamp}-${log.level}-${index}`}
                  className="flex gap-2 py-1 px-2 rounded hover:bg-slate-800/50 transition-colors"
                >
                  {/* Icône du niveau */}
                  <span className="flex-shrink-0 w-5 text-center">
                    {getLevelIcon(log.level)}
                  </span>

                  {/* Timestamp */}
                  {log.timestamp && (
                    <span className="flex-shrink-0 text-slate-500 w-32">
                      {log.timestamp.slice(11, 19)}
                    </span>
                  )}

                  {/* Level Badge */}
                  <span
                    className="flex-shrink-0 px-2 py-0.5 rounded text-[10px] font-bold uppercase w-20 text-center"
                    style={{
                      backgroundColor: `${getLevelColor(log.level)}22`,
                      color: getLevelColor(log.level),
                      border: `1px solid ${getLevelColor(log.level)}44`
                    }}
                  >
                    {log.level}
                  </span>

                  {/* Message */}
                  <span
                    className="flex-1 break-words"
                    style={{ color: getLevelColor(log.level) }}
                  >
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          ) : logs ? (
            <div className="text-center text-slate-500 italic py-8">
              <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <p>Aucun log correspondant au filtre {filterLevel}</p>
              <button
                onClick={() => setFilterLevel('ALL')}
                className="mt-2 text-blue-400 hover:text-blue-300 text-xs underline"
              >
                Afficher tous les logs
              </button>
            </div>
          ) : (
            <div className="text-slate-500 italic">
              <span className="text-emerald-400">$</span> Waiting for logs...
              <br />
              <span className="text-slate-600">→ Logs will appear here in real-time (refresh every 3s)</span>
            </div>
          )}
        </div>
        <div className="mt-2 text-xs text-slate-600 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            Auto-refresh: 3s | Auto-scroll: ON
          </div>
          {filterLevel !== 'ALL' && (
            <button
              onClick={() => setFilterLevel('ALL')}
              className="flex items-center gap-1 text-blue-400 hover:text-blue-300"
            >
              <X className="h-3 w-3" />
              Supprimer le filtre
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
