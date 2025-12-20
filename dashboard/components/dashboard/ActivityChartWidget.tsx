"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line } from 'recharts'
import { TrendingUp, Calendar } from "lucide-react"
import { useState, useEffect } from "react"

interface ActivityData {
  date: string
  messages: number
  visits: number
}

export function ActivityChartWidget() {
  const [data, setData] = useState<ActivityData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchActivityData = async () => {
      try {
        // Fetch activity for last 7 days from backend
        const res = await fetch('/api/history?days=7', { cache: 'no-store' })

        if (res.ok) {
          const historyData = await res.json()

          // Backend returns: { activity: [{date, messages, late_messages, visits, contacts}, ...], days: 7 }
          if (historyData.activity && Array.isArray(historyData.activity)) {
            // Transform backend data to chart format
            const chartData: ActivityData[] = historyData.activity.map((item: any) => {
              // Parse date from backend (format: YYYY-MM-DD)
              const dateObj = new Date(item.date + 'T00:00:00')
              const dateStr = dateObj.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })

              return {
                date: dateStr,
                messages: (item.messages || 0) + (item.late_messages || 0), // Total messages
                visits: item.visits || 0
              }
            })

            setData(chartData)
          } else {
            // Empty activity, fill with zeros for last 7 days
            setData(generateEmptyData())
          }
        } else {
          setData(generateEmptyData())
        }
      } catch (e) {
        setData(generateEmptyData())
      } finally {
        setLoading(false)
      }
    }

    // Helper to generate empty data for visualization
    const generateEmptyData = (): ActivityData[] => {
      const emptyData: ActivityData[] = []
      for (let i = 6; i >= 0; i--) {
        const date = new Date()
        date.setDate(date.getDate() - i)
        const dateStr = date.toLocaleDateString('fr-FR', { month: 'short', day: 'numeric' })
        emptyData.push({
          date: dateStr,
          messages: 0,
          visits: 0
        })
      }
      return emptyData
    }

    fetchActivityData()

    // Refresh every 5 minutes
    const interval = setInterval(fetchActivityData, 300000)
    return () => clearInterval(interval)
  }, [])

  if (loading) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="h-5 bg-slate-700 rounded w-1/3"></div>
        </CardHeader>
        <CardContent>
          <div className="h-64 bg-slate-800/50 rounded animate-pulse"></div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-base font-medium text-slate-200 flex items-center gap-2">
          <TrendingUp className="h-5 w-5" />
          Activité des 7 derniers jours
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="h-[300px] w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart
              data={data}
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
                  paddingTop: '20px',
                  fontSize: '14px'
                }}
                iconType="circle"
              />
              <Line
                type="monotone"
                dataKey="messages"
                stroke="#8b5cf6"
                strokeWidth={3}
                dot={{ fill: '#8b5cf6', r: 4 }}
                activeDot={{ r: 6 }}
                name="Messages envoyés"
              />
              <Line
                type="monotone"
                dataKey="visits"
                stroke="#14b8a6"
                strokeWidth={3}
                dot={{ fill: '#14b8a6', r: 4 }}
                activeDot={{ r: 6 }}
                name="Profils visités"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Summary stats */}
        <div className="grid grid-cols-2 gap-4 mt-4 pt-4 border-t border-slate-800">
          <div className="text-center">
            <div className="text-xs text-slate-400 mb-1">Total messages</div>
            <div className="text-xl font-bold text-purple-400">
              {data.reduce((sum, day) => sum + day.messages, 0)}
            </div>
          </div>
          <div className="text-center">
            <div className="text-xs text-slate-400 mb-1">Total visites</div>
            <div className="text-xl font-bold text-teal-400">
              {data.reduce((sum, day) => sum + day.visits, 0)}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
