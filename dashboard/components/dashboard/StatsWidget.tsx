"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, Mail, Eye } from "lucide-react"
import { useState, useEffect } from "react"
import { getBotStats, type BotStats } from "@/lib/api"

export function StatsWidget() {
  const [stats, setStats] = useState<BotStats | null>(null)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getBotStats()
        setStats(data)
      } catch (error) {
        console.error("Failed to fetch stats", error)
      }
    }

    fetchStats()
    // Refresh every minute
    const interval = setInterval(fetchStats, 60000)
    return () => clearInterval(interval)
  }, [])

  if (!stats) {
    return (
      <div className="grid gap-4 md:grid-cols-3">
        {Array(3).fill(0).map((_, index) => (
          <Card key={index} className="bg-slate-900 border-slate-800">
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <div className="h-4 bg-slate-700 rounded w-2/4"></div>
            </CardHeader>
            <CardContent>
              <div className="h-8 bg-slate-700 rounded w-1/4 mb-2"></div>
              <div className="h-3 bg-slate-700 rounded w-3/4"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const statItems = [
    {
      title: "Wishes Sent",
      value: stats.wishes_sent_total.toString(),
      icon: Mail,
      description: `+${stats.wishes_sent_today} today`
    },
    {
      title: "Profiles Visited",
      value: stats.profiles_visited_total.toString(),
      icon: Eye,
      description: `+${stats.profiles_visited_today} today`
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2">
      {statItems.map((stat, index) => (
        <Card key={index} className="bg-slate-900 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              {stat.title}
            </CardTitle>
            <stat.icon className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <p className="text-xs text-slate-500">
              {stat.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
