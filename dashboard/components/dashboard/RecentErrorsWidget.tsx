"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { AlertCircle, XCircle, AlertTriangle } from "lucide-react"
import { useState, useEffect } from "react"

interface ErrorEntry {
  id: number
  timestamp: string
  type: string
  message: string
  severity: 'error' | 'warning' | 'critical'
}

export function RecentErrorsWidget() {
  const [errors, setErrors] = useState<ErrorEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchErrors = async () => {
      try {
        const res = await fetch('/api/history?type=error&limit=5', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          // Transform history data to errors
          const errorList = (data.history || []).slice(0, 5).map((item: any, index: number) => ({
            id: item.id || index,
            timestamp: item.timestamp || new Date().toISOString(),
            type: item.type || 'Unknown',
            message: item.message || item.details || 'Unknown error',
            severity: item.severity || 'error'
          }))
          setErrors(errorList)
        }
      } catch (e) {
        console.error("Failed to fetch errors", e)
      } finally {
        setLoading(false)
      }
    }

    fetchErrors()

    // Refresh every 2 minutes
    const interval = setInterval(fetchErrors, 120000)
    return () => clearInterval(interval)
  }, [])

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

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-200 flex items-center gap-2">
          <AlertCircle className="h-5 w-5 text-red-400" />
          Erreurs récentes
        </CardTitle>
      </CardHeader>
      <CardContent>
        {errors.length === 0 ? (
          <div className="text-center py-6">
            <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-emerald-500/10 mb-2">
              <AlertCircle className="h-6 w-6 text-emerald-400" />
            </div>
            <p className="text-sm text-slate-400">Aucune erreur récente</p>
          </div>
        ) : (
          <div className="space-y-3">
            {errors.map((error) => (
              <div
                key={error.id}
                className="p-3 rounded-lg border border-slate-800 bg-slate-800/30 hover:bg-slate-800/50 transition-colors"
              >
                {/* Header: Type + Time */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <Badge
                    variant="outline"
                    className={`${getSeverityColor(error.severity)} flex items-center gap-1`}
                  >
                    {getSeverityIcon(error.severity)}
                    <span className="text-xs font-medium">{error.type}</span>
                  </Badge>
                  <span className="text-xs text-slate-500">
                    {formatTimestamp(error.timestamp)}
                  </span>
                </div>

                {/* Message */}
                <p className="text-xs text-slate-300 leading-relaxed line-clamp-2">
                  {error.message}
                </p>
              </div>
            ))}
          </div>
        )}

        {/* View all link */}
        {errors.length > 0 && (
          <div className="mt-4 pt-3 border-t border-slate-800">
            <a
              href="/history?filter=error"
              className="text-xs text-slate-400 hover:text-slate-300 transition-colors flex items-center justify-center gap-1"
            >
              Voir toutes les erreurs
              <span className="text-slate-600">→</span>
            </a>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
