"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, Mail, Eye } from "lucide-react"
import { useState, useEffect } from "react"
import { api, type BotStats } from "@/lib/api"

export function StatsWidget() {
  const [stats, setStats] = useState<BotStats>({
    messages_sent: 0,
    profiles_visited: 0,
    contacts_found: 0,
    messages_24h: 0,
    profiles_24h: 0,
    contacts_24h: 0
  })

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await api.getStats()
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

  const statItems = [
    {
      title: "Messages Sent",
      value: stats.messages_sent.toString(),
      icon: Mail,
      description: `+${stats.messages_24h} from yesterday`
    },
    {
      title: "Profiles Visited",
      value: stats.profiles_visited.toString(),
      icon: Eye,
      description: `+${stats.profiles_24h} from yesterday`
    },
    {
      title: "Contacts Found",
      value: stats.contacts_found.toString(),
      icon: Users,
      description: `+${stats.contacts_24h} from yesterday`
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-3">
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
