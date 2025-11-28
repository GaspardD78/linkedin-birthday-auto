"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import {
  AlertCircle,
  XCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Copy,
  RefreshCw,
  Bug,
  ExternalLink
} from "lucide-react"
import { useState, useEffect } from "react"

interface ErrorEntry {
  id: number
  timestamp: string
  type: string
  message: string
  severity: 'error' | 'warning' | 'critical'
  details?: string
  stack?: string
  context?: {
    source?: string
    action?: string
    url?: string
    [key: string]: any
  }
}

export function RecentErrorsWidget() {
  const [errors, setErrors] = useState<ErrorEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedError, setExpandedError] = useState<number | null>(null)
  const [filterSeverity, setFilterSeverity] = useState<string>('all')

  const fetchErrors = async () => {
    try {
      const res = await fetch('/api/history?type=error&limit=10', { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        // Transform history data to errors
        const errorList = (data.history || []).slice(0, 10).map((item: any, index: number) => ({
          id: item.id || index,
          timestamp: item.timestamp || new Date().toISOString(),
          type: item.type || 'Unknown',
          message: item.message || item.details || 'Unknown error',
          severity: item.severity || 'error',
          details: item.details || item.message,
          stack: item.stack,
          context: item.context || {}
        }))
        setErrors(errorList)
      }
    } catch (e) {
      console.error("Failed to fetch errors", e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchErrors()

    // Refresh every 30 seconds
    const interval = setInterval(fetchErrors, 30000)
    return () => clearInterval(interval)
  }, [])

  const handleRefresh = () => {
    setLoading(true)
    fetchErrors()
  }

  const copyErrorDetails = (error: ErrorEntry) => {
    const details = `
ERROR REPORT
============
Time: ${error.timestamp}
Type: ${error.type}
Severity: ${error.severity}
Message: ${error.message}
${error.details ? `\nDetails: ${error.details}` : ''}
${error.stack ? `\nStack: ${error.stack}` : ''}
${error.context ? `\nContext: ${JSON.stringify(error.context, null, 2)}` : ''}
    `.trim()

    navigator.clipboard.writeText(details)
    alert('✅ Erreur copiée dans le presse-papier')
  }

  const filteredErrors = errors.filter(error =>
    filterSeverity === 'all' || error.severity === filterSeverity
  )

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case 'critical':
        return <XCircle className="h-4 w-4" />
      case 'warning':
        return <AlertTriangle className="h-4 w-4" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-500/10 text-red-400 border-red-500/20'
      case 'warning':
        return 'bg-orange-500/10 text-orange-400 border-orange-500/20'
      default:
        return 'bg-red-500/10 text-red-400 border-red-500/20'
    }
  }

  const formatTimestamp = (timestamp: string) => {
    try {
      const date = new Date(timestamp)
      return date.toLocaleTimeString('fr-FR', {
        hour: '2-digit',
        minute: '2-digit'
      })
    } catch {
      return timestamp
    }
  }

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-5 bg-slate-700 rounded w-1/2"></div>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {Array(3).fill(0).map((_, i) => (
              <div key={i} className="space-y-2">
                <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                <div className="h-3 bg-slate-700 rounded w-full"></div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    )
  }

  const severityStats = {
    critical: errors.filter(e => e.severity === 'critical').length,
    error: errors.filter(e => e.severity === 'error').length,
    warning: errors.filter(e => e.severity === 'warning').length
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bug className="h-5 w-5 text-red-400" />
            <CardTitle className="text-base font-medium text-slate-200">
              Erreurs & Warnings
            </CardTitle>
            <Badge className="bg-red-600/20 text-red-400 border-red-600/50">
              {errors.length}
            </Badge>
          </div>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-slate-500 hover:text-blue-400"
            onClick={handleRefresh}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
        </div>

        {/* Severity Filter */}
        <div className="flex gap-2 mt-3">
          <button
            onClick={() => setFilterSeverity('all')}
            className={`px-2 py-1 rounded text-xs transition-all ${
              filterSeverity === 'all'
                ? 'bg-slate-700 text-white'
                : 'bg-slate-800 text-slate-400 hover:bg-slate-700'
            }`}
          >
            Tout ({errors.length})
          </button>
          <button
            onClick={() => setFilterSeverity('critical')}
            className={`px-2 py-1 rounded text-xs transition-all ${
              filterSeverity === 'critical'
                ? 'bg-red-600 text-white'
                : 'bg-red-600/20 text-red-400 hover:bg-red-600/30'
            }`}
          >
            🔴 Critical ({severityStats.critical})
          </button>
          <button
            onClick={() => setFilterSeverity('error')}
            className={`px-2 py-1 rounded text-xs transition-all ${
              filterSeverity === 'error'
                ? 'bg-red-500 text-white'
                : 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
            }`}
          >
            🟠 Error ({severityStats.error})
          </button>
          <button
            onClick={() => setFilterSeverity('warning')}
            className={`px-2 py-1 rounded text-xs transition-all ${
              filterSeverity === 'warning'
                ? 'bg-orange-500 text-white'
                : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30'
            }`}
          >
            🟡 Warning ({severityStats.warning})
          </button>
        </div>
      </CardHeader>

      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {Array(3).fill(0).map((_, i) => (
              <div key={i} className="space-y-2 p-3 rounded-lg bg-slate-800/30">
                <div className="h-4 bg-slate-700 rounded w-3/4"></div>
                <div className="h-3 bg-slate-700 rounded w-full"></div>
              </div>
            ))}
          </div>
        ) : filteredErrors.length === 0 ? (
          <div className="text-center py-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/10 mb-2">
              <AlertCircle className="h-6 w-6 text-emerald-400" />
            </div>
            <p className="text-sm text-slate-400">
              {filterSeverity === 'all' ? 'Aucune erreur récente' : `Aucune erreur de type ${filterSeverity}`}
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[400px] overflow-y-auto custom-scrollbar">
            {filteredErrors.slice(0, 5).map((error) => (
              <div
                key={error.id}
                className={`rounded-lg border transition-all ${
                  expandedError === error.id
                    ? 'border-red-600/50 bg-red-900/10'
                    : 'border-slate-800 bg-slate-800/30 hover:bg-slate-800/50'
                }`}
              >
                {/* Header: Type + Time + Actions */}
                <div className="p-3">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="flex items-center gap-2 flex-1 min-w-0">
                      <Badge
                        variant="outline"
                        className={`${getSeverityColor(error.severity)} flex items-center gap-1 flex-shrink-0`}
                      >
                        {getSeverityIcon(error.severity)}
                        <span className="text-[10px] font-bold uppercase">{error.severity}</span>
                      </Badge>
                      <span className="text-xs text-slate-400 truncate">{error.type}</span>
                    </div>
                    <div className="flex items-center gap-1 flex-shrink-0">
                      <span className="text-xs text-slate-500">
                        {formatTimestamp(error.timestamp)}
                      </span>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-slate-500 hover:text-blue-400"
                        onClick={() => copyErrorDetails(error)}
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="h-6 w-6 text-slate-500 hover:text-blue-400"
                        onClick={() => setExpandedError(expandedError === error.id ? null : error.id)}
                      >
                        {expandedError === error.id ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Message */}
                  <p className={`text-xs text-slate-300 leading-relaxed ${expandedError === error.id ? '' : 'line-clamp-2'}`}>
                    {error.message}
                  </p>

                  {/* Context */}
                  {error.context && Object.keys(error.context).length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {error.context.source && (
                        <Badge variant="outline" className="bg-slate-800 text-slate-400 border-slate-700 text-[10px]">
                          📍 {error.context.source}
                        </Badge>
                      )}
                      {error.context.action && (
                        <Badge variant="outline" className="bg-slate-800 text-slate-400 border-slate-700 text-[10px]">
                          ⚙️ {error.context.action}
                        </Badge>
                      )}
                    </div>
                  )}
                </div>

                {/* Expanded Details */}
                {expandedError === error.id && (
                  <div className="px-3 pb-3 space-y-2 border-t border-slate-800">
                    {error.details && error.details !== error.message && (
                      <div className="mt-2">
                        <div className="text-[10px] font-semibold text-slate-500 mb-1">DÉTAILS:</div>
                        <div className="text-xs text-slate-400 bg-slate-900/50 rounded p-2 font-mono">
                          {error.details}
                        </div>
                      </div>
                    )}

                    {error.stack && (
                      <div>
                        <div className="text-[10px] font-semibold text-slate-500 mb-1">STACK TRACE:</div>
                        <div className="text-[10px] text-slate-500 bg-slate-900/50 rounded p-2 font-mono max-h-32 overflow-y-auto custom-scrollbar">
                          {error.stack}
                        </div>
                      </div>
                    )}

                    {error.context && Object.keys(error.context).length > 0 && (
                      <div>
                        <div className="text-[10px] font-semibold text-slate-500 mb-1">CONTEXTE:</div>
                        <div className="text-[10px] text-slate-500 bg-slate-900/50 rounded p-2 font-mono">
                          <pre className="whitespace-pre-wrap">{JSON.stringify(error.context, null, 2)}</pre>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* View all link */}
        {filteredErrors.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-800">
            <a
              href="/history?filter=error"
              className="text-xs text-slate-400 hover:text-slate-300 transition-colors flex items-center justify-center gap-1"
            >
              Voir toutes les erreurs
              <ExternalLink className="h-3 w-3" />
            </a>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
