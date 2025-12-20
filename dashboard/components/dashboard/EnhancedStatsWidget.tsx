"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Mail, Eye, Users, AlertCircle } from "lucide-react"
import { useState, useEffect } from "react"
import { getBotStats, type BotStats } from "../../lib/api"

interface StatCard {
  title: string
  value: string
  icon: React.ElementType
  gradient: string
  textColor: string
  description?: string
}

export function EnhancedStatsWidget() {
  const [stats, setStats] = useState<BotStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uniqueContacts, setUniqueContacts] = useState<number>(0)
  const [errorCount, setErrorCount] = useState<number>(0)

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const data = await getBotStats()
        setStats(data)
        setError(null)
      } catch (error) {
        const errorMsg = error instanceof Error ? error.message : "Échec de connexion à l'API"
        setError(errorMsg)
      }
    }

    // Fetch unique contacts count
    const fetchContacts = async () => {
      try {
        const res = await fetch('/api/contacts', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setUniqueContacts(data.contacts?.length || 0)
        }
      } catch (e) {
      }
    }

    // Fetch error count
    const fetchErrors = async () => {
      try {
        const res = await fetch('/api/history?type=error', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          setErrorCount(data.history?.length || 0)
        }
      } catch (e) {
      }
    }

    fetchStats()
    fetchContacts()
    fetchErrors()

    // Refresh every minute
    const interval = setInterval(() => {
      fetchStats()
      fetchContacts()
      fetchErrors()
    }, 60000)

    return () => clearInterval(interval)
  }, [])

  if (error) {
    return (
      <Card className="bg-red-900/20 border-red-600">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!stats) {
    return (
      <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={`skeleton-${index}`} className="bg-slate-900 border-slate-800 overflow-hidden">
            <CardContent className="p-6">
              <div className="h-4 bg-slate-700 rounded w-2/3 mb-4"></div>
              <div className="h-8 bg-slate-700 rounded w-1/2 mb-2"></div>
              <div className="h-3 bg-slate-700 rounded w-3/4"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const statCards: StatCard[] = [
    {
      title: "Messages envoyés",
      value: stats.wishes_sent_total.toString(),
      icon: Mail,
      gradient: "from-purple-500 to-indigo-600",
      textColor: "text-purple-100",
      description: `+${stats.wishes_sent_today} aujourd'hui`
    },
    {
      title: "Profils visités",
      value: stats.profiles_visited_total.toString(),
      icon: Eye,
      gradient: "from-teal-500 to-emerald-500",
      textColor: "text-teal-100",
      description: `+${stats.profiles_visited_today} aujourd'hui`
    },
    {
      title: "Contacts uniques",
      value: uniqueContacts.toString(),
      icon: Users,
      gradient: "from-cyan-500 to-blue-500",
      textColor: "text-cyan-100",
      description: "Base de données"
    },
    {
      title: "Erreurs",
      value: errorCount.toString(),
      icon: AlertCircle,
      gradient: "from-pink-500 to-rose-500",
      textColor: "text-pink-100",
      description: "Historique complet"
    }
  ]

  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
      {statCards.map((stat) => (
        <Card
          key={stat.title}
          className={`bg-gradient-to-br ${stat.gradient} border-0 shadow-lg hover:shadow-xl transition-all duration-300 hover:scale-105 overflow-hidden`}
        >
          <CardContent className="p-6 relative">
            {/* Icon background decoration */}
            <div className="absolute -right-4 -top-4 opacity-20">
              <stat.icon className="h-24 w-24" />
            </div>

            {/* Content */}
            <div className="relative z-10">
              <div className="flex items-center justify-between mb-3">
                <h3 className={`text-sm font-medium ${stat.textColor} opacity-90`}>
                  {stat.title}
                </h3>
                <stat.icon className={`h-5 w-5 ${stat.textColor}`} />
              </div>

              <div className="text-3xl font-bold text-white mb-1">
                {stat.value}
              </div>

              {stat.description && (
                <p className={`text-xs ${stat.textColor} opacity-75`}>
                  {stat.description}
                </p>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
