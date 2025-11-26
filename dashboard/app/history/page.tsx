"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Loader2, Calendar, TrendingUp } from "lucide-react"

interface DailyActivity {
  date: string
  messages: number
  late_messages: number
  visits: number
  contacts: number
}

export default function HistoryPage() {
  const [activity, setActivity] = useState<DailyActivity[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchActivity()
  }, [])

  const fetchActivity = async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch('/api/history?days=30')

      if (!response.ok) {
        throw new Error('Failed to fetch activity data')
      }

      const data = await response.json()
      setActivity(data.activity || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric'
    })
  }

  const getBadgeVariant = (value: number) => {
    if (value === 0) return "secondary"
    return "default"
  }

  const getBadgeColor = (value: number) => {
    if (value === 0) return "bg-slate-700 text-slate-300"
    return "bg-emerald-600 text-white"
  }

  const getTotalStats = () => {
    return activity.reduce((acc, day) => ({
      totalMessages: acc.totalMessages + day.messages,
      totalLate: acc.totalLate + day.late_messages,
      totalVisits: acc.totalVisits + day.visits,
      totalOnTime: acc.totalOnTime + (day.messages - day.late_messages)
    }), { totalMessages: 0, totalLate: 0, totalVisits: 0, totalOnTime: 0 })
  }

  const stats = getTotalStats()

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Calendar className="h-8 w-8 text-blue-400" />
        <div>
          <h1 className="text-3xl font-bold text-white">Historique & Statistiques</h1>
          <p className="text-slate-400">Suivi détaillé de l'activité quotidienne sur 30 jours</p>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Messages Totaux</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stats.totalMessages}</div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">À l'heure</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-emerald-500">{stats.totalOnTime}</div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">En retard</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-amber-500">{stats.totalLate}</div>
          </CardContent>
        </Card>

        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400">Visites Profils</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-500">{stats.totalVisits}</div>
          </CardContent>
        </Card>
      </div>

      {/* Activity Table */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <TrendingUp className="h-5 w-5" />
            Tableau de Bord Journalier
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="ml-3 text-slate-400">Chargement des données...</span>
            </div>
          ) : error ? (
            <div className="text-center py-12">
              <p className="text-red-400">❌ {error}</p>
              <button
                onClick={fetchActivity}
                className="mt-4 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-md transition-colors"
              >
                Réessayer
              </button>
            </div>
          ) : activity.length === 0 ? (
            <div className="text-center py-12 text-slate-400">
              Aucune activité enregistrée pour les 30 derniers jours
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-slate-800">
                    <th className="text-left py-3 px-4 text-sm font-semibold text-slate-300">
                      📅 Date
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-slate-300">
                      ✉️ Messages Totaux
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-slate-300">
                      ✅ À l'heure
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-slate-300">
                      ⏰ En retard
                    </th>
                    <th className="text-center py-3 px-4 text-sm font-semibold text-slate-300">
                      👀 Visites Profils
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {activity.map((day, index) => {
                    const onTimeMessages = day.messages - day.late_messages
                    return (
                      <tr
                        key={day.date}
                        className="border-b border-slate-800 hover:bg-slate-800/50 transition-colors"
                      >
                        <td className="py-3 px-4 text-sm text-slate-200 font-medium">
                          {formatDate(day.date)}
                        </td>
                        <td className="text-center py-3 px-4">
                          <Badge className={getBadgeColor(day.messages)}>
                            {day.messages}
                          </Badge>
                        </td>
                        <td className="text-center py-3 px-4">
                          <Badge className={getBadgeColor(onTimeMessages)}>
                            {onTimeMessages}
                          </Badge>
                        </td>
                        <td className="text-center py-3 px-4">
                          <Badge className={day.late_messages > 0 ? "bg-amber-600 text-white" : "bg-slate-700 text-slate-300"}>
                            {day.late_messages}
                          </Badge>
                        </td>
                        <td className="text-center py-3 px-4">
                          <Badge className={day.visits > 0 ? "bg-blue-600 text-white" : "bg-slate-700 text-slate-300"}>
                            {day.visits}
                          </Badge>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
