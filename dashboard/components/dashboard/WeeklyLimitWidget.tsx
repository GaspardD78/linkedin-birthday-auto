"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { AlertTriangle, TrendingUp } from "lucide-react"
import { useState, useEffect } from "react"

const WEEKLY_LIMIT = 100 // LinkedIn weekly connection limit

export function WeeklyLimitWidget() {
  const [weeklyCount, setWeeklyCount] = useState<number>(0)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchWeeklyStats = async () => {
      try {
        // Get stats from last 7 days
        const res = await fetch('/api/stats', {
          credentials: 'same-origin'
        })
        if (res.ok) {
          const data = await res.json()
          // Use wishes_sent_week which returns messages from last 7 days
          setWeeklyCount(data.wishes_sent_week || 0)
        }
      } catch (e) {
      } finally {
        setLoading(false)
      }
    }

    fetchWeeklyStats()

    // Refresh every 5 minutes
    const interval = setInterval(fetchWeeklyStats, 300000)
    return () => clearInterval(interval)
  }, [])

  const percentage = Math.min((weeklyCount / WEEKLY_LIMIT) * 100, 100)
  const remaining = Math.max(WEEKLY_LIMIT - weeklyCount, 0)

  // Determine color based on percentage (like V1)
  const getProgressColor = () => {
    if (percentage >= 90) return "bg-red-500"
    if (percentage >= 70) return "bg-orange-500"
    return "bg-emerald-500"
  }

  const getTextColor = () => {
    if (percentage >= 90) return "text-red-400"
    if (percentage >= 70) return "text-orange-400"
    return "text-emerald-400"
  }

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-5 bg-slate-700 rounded w-1/3"></div>
        </CardHeader>
        <CardContent>
          <div className="h-4 bg-slate-700 rounded w-full mb-2"></div>
          <div className="h-3 bg-slate-700 rounded w-1/2"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-200 flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Limite hebdomadaire LinkedIn
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Progress bar */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-sm">
            <span className="text-slate-400">
              {weeklyCount} / {WEEKLY_LIMIT} messages
            </span>
            <span className={`font-semibold ${getTextColor()}`}>
              {percentage.toFixed(1)}%
            </span>
          </div>

          <div className="relative h-3 bg-slate-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${getProgressColor()} transition-all duration-500 ease-out rounded-full`}
              style={{ width: `${percentage}%` }}
            />
          </div>
        </div>

        {/* Status message */}
        <div className="flex items-start gap-2 text-xs">
          {percentage >= 90 ? (
            <>
              <AlertTriangle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" />
              <span className="text-red-400">
                Attention ! Vous approchez de la limite hebdomadaire LinkedIn
              </span>
            </>
          ) : percentage >= 70 ? (
            <>
              <AlertTriangle className="h-4 w-4 text-orange-400 flex-shrink-0 mt-0.5" />
              <span className="text-orange-400">
                Il vous reste {remaining} messages cette semaine
              </span>
            </>
          ) : (
            <span className="text-slate-400">
              ✓ Vous êtes dans les limites. Encore {remaining} messages disponibles.
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
