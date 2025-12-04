"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { Badge } from "@/components/ui/badge"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { TrendingUp, Activity, AlertTriangle, Eye } from "lucide-react"
import { useState, useEffect } from "react"
import Link from "next/link"

interface ActivityData {
  date: string
  messages: number
  visits: number
  errors: number
}

interface LogEntry {
  timestamp: string
  level: string
  message: string
  event: string
}

export function ActivityMonitor() {
  const [activityData, setActivityData] = useState<ActivityData[]>([])
  const [recentLogs, setRecentLogs] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState("chart")

  useEffect(() => {
    const fetchData = async () => {
      try {
        // Fetch activity data
        const activityRes = await fetch('/api/history?days=7', { cache: 'no-store' })
        if (activityRes.ok) {
          const historyData = await activityRes.json()
          if (historyData.activity && Array.isArray(historyData.activity)) {
            const chartData: ActivityData[] = historyData.activity.map((item: any) => {
              const dateObj = new Date(item.date + 'T00:00:00')
              const dateStr = dateObj.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
              return {
                date: dateStr,
                messages: (item.messages || 0) + (item.late_messages || 0),
                visits: item.visits || 0,
                errors: item.errors || 0
              }
            })
            setActivityData(chartData)
          }
        }

        // Fetch recent logs
        const logsRes = await fetch('/api/logs?limit=20', { cache: 'no-store' })
        if (logsRes.ok) {
          const logsData = await logsRes.json()
          setRecentLogs(logsData.logs || [])
        }
      } catch (error) {
        console.error("Failed to fetch activity data:", error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
    const interval = setInterval(fetchData, 30000) // Refresh every 30 seconds
    return () => clearInterval(interval)
  }, [])

  const formatLogLine = (log: string) => {
    try {
      const parsed = JSON.parse(log)
      const level = (parsed.level || 'INFO').toUpperCase()
      const message = parsed.event || parsed.message || log
      const timestamp = parsed.timestamp || parsed.event_time || ''

      let levelColor = 'text-slate-400'
      let bgColor = 'hover:bg-slate-800/50'

      if (level.includes('ERROR') || level.includes('CRITICAL')) {
        levelColor = 'text-red-400'
        bgColor = 'hover:bg-red-900/20'
      } else if (level.includes('WARNING') || level.includes('WARN')) {
        levelColor = 'text-amber-400'
        bgColor = 'hover:bg-amber-900/20'
      } else if (level.includes('SUCCESS')) {
        levelColor = 'text-emerald-400'
        bgColor = 'hover:bg-emerald-900/20'
      } else if (level.includes('INFO')) {
        levelColor = 'text-blue-400'
        bgColor = 'hover:bg-blue-900/20'
      }

      return (
        <div className={`px-3 py-2 rounded transition-colors ${bgColor} border-l-2 border-transparent hover:border-l-2 hover:border-${levelColor.split('-')[1]}-500`}>
          <div className="flex items-start gap-3">
            <span className="text-slate-500 text-[10px] font-mono min-w-[60px]">
              {timestamp.slice(11, 19)}
            </span>
            <span className={`text-[10px] font-bold ${levelColor} min-w-[60px]`}>
              [{level}]
            </span>
            <span className="text-xs text-slate-300 flex-1 break-words">
              {message}
            </span>
          </div>
        </div>
      )
    } catch {
      return (
        <div className="px-3 py-2 rounded hover:bg-slate-800/50 text-xs text-slate-400">
          {log}
        </div>
      )
    }
  }

  const totalMessages = activityData.reduce((sum, day) => sum + day.messages, 0)
  const totalVisits = activityData.reduce((sum, day) => sum + day.visits, 0)
  const totalErrors = activityData.reduce((sum, day) => sum + day.errors, 0)

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-5 bg-slate-700 rounded w-1/3 animate-pulse"></div>
        </CardHeader>
        <CardContent>
          <div className="h-96 bg-slate-800/50 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold text-slate-200 flex items-center gap-2">
            <Activity className="h-5 w-5 text-cyan-500" />
            Monitoring d'Activité
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="border-slate-700 text-slate-400">
              7 derniers jours
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-2 bg-slate-800/50 p-1">
            <TabsTrigger
              value="chart"
              className="data-[state=active]:bg-slate-700 data-[state=active]:text-white"
            >
              <TrendingUp className="h-4 w-4 mr-2" />
              Graphique
            </TabsTrigger>
            <TabsTrigger
              value="logs"
              className="data-[state=active]:bg-slate-700 data-[state=active]:text-white"
            >
              <Activity className="h-4 w-4 mr-2" />
              Logs Récents
            </TabsTrigger>
          </TabsList>

          {/* Chart Tab */}
          <TabsContent value="chart" className="mt-4 space-y-4">
            <div className="h-[300px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={activityData}
                  margin={{ top: 5, right: 20, left: 0, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#334155" />
                  <XAxis
                    dataKey="date"
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                  />
                  <YAxis
                    stroke="#64748b"
                    fontSize={12}
                    tickLine={false}
                    axisLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #334155',
                      borderRadius: '8px',
                      color: '#e2e8f0'
                    }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Legend
                    wrapperStyle={{
                      paddingTop: '10px',
                      fontSize: '12px'
                    }}
                    iconType="circle"
                  />
                  <Line
                    type="monotone"
                    dataKey="messages"
                    stroke="#8b5cf6"
                    strokeWidth={2}
                    dot={{ fill: '#8b5cf6', r: 3 }}
                    activeDot={{ r: 5 }}
                    name="Messages"
                  />
                  <Line
                    type="monotone"
                    dataKey="visits"
                    stroke="#14b8a6"
                    strokeWidth={2}
                    dot={{ fill: '#14b8a6', r: 3 }}
                    activeDot={{ r: 5 }}
                    name="Visites"
                  />
                  {totalErrors > 0 && (
                    <Line
                      type="monotone"
                      dataKey="errors"
                      stroke="#ef4444"
                      strokeWidth={2}
                      dot={{ fill: '#ef4444', r: 3 }}
                      activeDot={{ r: 5 }}
                      name="Erreurs"
                    />
                  )}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Summary Stats */}
            <div className="grid grid-cols-3 gap-4 pt-4 border-t border-slate-800">
              <div className="text-center">
                <div className="text-xs text-slate-400 mb-1">Messages</div>
                <div className="text-2xl font-bold text-purple-400">{totalMessages}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-400 mb-1">Visites</div>
                <div className="text-2xl font-bold text-teal-400">{totalVisits}</div>
              </div>
              <div className="text-center">
                <div className="text-xs text-slate-400 mb-1">Erreurs</div>
                <div className={`text-2xl font-bold ${totalErrors > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
                  {totalErrors}
                </div>
              </div>
            </div>
          </TabsContent>

          {/* Logs Tab */}
          <TabsContent value="logs" className="mt-4">
            <div className="bg-slate-950 rounded-lg p-4 font-mono text-xs space-y-1 max-h-[400px] overflow-y-auto border border-slate-800">
              {recentLogs.length > 0 ? (
                recentLogs.map((log, idx) => (
                  <div key={idx}>
                    {formatLogLine(log)}
                  </div>
                ))
              ) : (
                <div className="text-center py-8 text-slate-600">
                  <Activity className="h-8 w-8 mx-auto mb-2 opacity-50" />
                  <p>Aucun log disponible</p>
                </div>
              )}
            </div>

            {/* View More Link */}
            <div className="mt-4 text-center">
              <Link href="/logs">
                <span className="text-xs text-cyan-400 hover:text-cyan-300 hover:underline cursor-pointer inline-flex items-center gap-1">
                  <Eye className="h-3 w-3" />
                  Voir tous les logs
                </span>
              </Link>
            </div>
          </TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
