"use client"

import { Card, CardContent } from "@/components/ui/card"
import { Mail, Eye, Users, AlertCircle, TrendingUp, Calendar } from "lucide-react"
import { useState, useEffect } from "react"
import { getBotStats, type BotStats } from "@/lib/api"

interface KPICard {
  title: string
  value: string
  subtitle: string
  icon: React.ElementType
  colorKey: 'blue' | 'emerald' | 'purple' | 'cyan'
  trend?: {
    value: string
    positive: boolean
  }
}

interface ActivityDay {
  messages: number
}

const colorClasses = {
  blue: {
    accent: 'bg-gradient-to-r from-blue-500 to-blue-600',
    iconBg: 'bg-blue-500/10',
    iconBorder: 'border-blue-500/20',
    iconColor: 'text-blue-400'
  },
  emerald: {
    accent: 'bg-gradient-to-r from-emerald-500 to-emerald-600',
    iconBg: 'bg-emerald-500/10',
    iconBorder: 'border-emerald-500/20',
    iconColor: 'text-emerald-400'
  },
  purple: {
    accent: 'bg-gradient-to-r from-purple-500 to-purple-600',
    iconBg: 'bg-purple-500/10',
    iconBorder: 'border-purple-500/20',
    iconColor: 'text-purple-400'
  },
  cyan: {
    accent: 'bg-gradient-to-r from-cyan-500 to-cyan-600',
    iconBg: 'bg-cyan-500/10',
    iconBorder: 'border-cyan-500/20',
    iconColor: 'text-cyan-400'
  }
}

export function KPICards() {
  const [stats, setStats] = useState<BotStats | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [uniqueContacts, setUniqueContacts] = useState<number>(0)
  const [errorCount, setErrorCount] = useState<number>(0)
  const [weeklyMessages, setWeeklyMessages] = useState<number>(0)

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
        // Silently fail - contacts fetch is not critical
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
        // Silently fail - error count fetch is not critical
      }
    }

    // Fetch weekly messages
    const fetchWeeklyMessages = async () => {
      try {
        const res = await fetch('/api/history?days=7', { cache: 'no-store' })
        if (res.ok) {
          const data = await res.json()
          const total = data.activity?.reduce((sum: number, day: ActivityDay) => sum + (day.messages || 0), 0) || 0
          setWeeklyMessages(total)
        }
      } catch (e) {
        // Silently fail - weekly stats fetch is not critical
      }
    }

    fetchStats()
    fetchContacts()
    fetchErrors()
    fetchWeeklyMessages()

    // Refresh every minute
    const interval = setInterval(() => {
      fetchStats()
      fetchContacts()
      fetchErrors()
      fetchWeeklyMessages()
    }, 60000)

    return () => clearInterval(interval)
  }, [])

  if (error) {
    return (
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-6">
          <div className="flex items-center gap-2 text-red-400">
            <AlertCircle className="h-5 w-5" aria-hidden="true" />
            <p className="text-sm">{error}</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!stats) {
    return (
      <div
        className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4"
        role="status"
        aria-label="Chargement des indicateurs clés"
        aria-busy="true"
      >
        {Array.from({ length: 4 }).map((_, index) => (
          <Card key={`skeleton-${index}`} className="bg-slate-900 border-slate-800 overflow-hidden">
            <CardContent className="p-6">
              <div className="h-4 bg-slate-700 rounded w-2/3 mb-4 animate-pulse"></div>
              <div className="h-8 bg-slate-700 rounded w-1/2 mb-2 animate-pulse"></div>
              <div className="h-3 bg-slate-700 rounded w-3/4 animate-pulse"></div>
            </CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const kpiCards: KPICard[] = [
    {
      title: "Messages Envoyés",
      value: stats.wishes_sent_total.toString(),
      subtitle: `+${stats.wishes_sent_today} aujourd'hui`,
      icon: Mail,
      colorKey: "blue",
      trend: stats.wishes_sent_today > 0 ? {
        value: `+${stats.wishes_sent_today}`,
        positive: true
      } : undefined
    },
    {
      title: "Profils Visités",
      value: stats.profiles_visited_total.toString(),
      subtitle: `+${stats.profiles_visited_today} aujourd'hui`,
      icon: Eye,
      colorKey: "emerald",
      trend: stats.profiles_visited_today > 0 ? {
        value: `+${stats.profiles_visited_today}`,
        positive: true
      } : undefined
    },
    {
      title: "Cette Semaine",
      value: weeklyMessages.toString(),
      subtitle: "Messages envoyés (7j)",
      icon: Calendar,
      colorKey: "purple",
      trend: weeklyMessages > 0 ? {
        value: `${weeklyMessages} msg`,
        positive: true
      } : undefined
    },
    {
      title: "Contacts Uniques",
      value: uniqueContacts.toString(),
      subtitle: "Base de données",
      icon: Users,
      colorKey: "cyan",
    }
  ]

  return (
    <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4" aria-label="Indicateurs clés de performance">
      {kpiCards.map((kpi) => {
        const colors = colorClasses[kpi.colorKey]
        return (
          <Card
            key={kpi.title}
            className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all duration-300 hover:shadow-lg overflow-hidden group"
          >
            <CardContent className="p-6 relative">

              {/* Gradient Accent Line */}
              <div className={`absolute top-0 left-0 right-0 h-1 ${colors.accent}`} />

              {/* Icon Background Decoration */}
              <div className={`absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity`}>
                <kpi.icon className="h-32 w-32" aria-hidden="true" />
              </div>

              {/* Content */}
              <div className="relative z-10">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-2 rounded-lg ${colors.iconBg} border ${colors.iconBorder}`}>
                    <kpi.icon className={`h-5 w-5 ${colors.iconColor}`} aria-hidden="true" />
                  </div>
                {kpi.trend && (
                  <div className={`flex items-center gap-1 text-xs px-2 py-1 rounded-full ${kpi.trend.positive ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>
                    <TrendingUp className={`h-3 w-3 ${!kpi.trend.positive && 'rotate-180'}`} aria-hidden="true" />
                    <span className="font-semibold">{kpi.trend.value}</span>
                  </div>
                )}
              </div>

              {/* Title */}
              <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
                {kpi.title}
              </h3>

              {/* Value */}
              <div className="text-3xl font-bold text-white mb-1">
                {kpi.value}
              </div>

              {/* Subtitle */}
              <p className="text-xs text-slate-500">
                {kpi.subtitle}
              </p>
            </div>
          </CardContent>
        </Card>
        )
      })}

      {/* Error Card (5th card) */}
      <Card
        className={`bg-slate-900 border-slate-800 hover:border-slate-700 transition-all duration-300 hover:shadow-lg overflow-hidden group ${errorCount > 0 ? 'border-red-500/30' : ''}`}
      >
        <CardContent className="p-6 relative">

          {/* Gradient Accent Line */}
          <div className={`absolute top-0 left-0 right-0 h-1 ${errorCount > 0 ? 'bg-gradient-to-r from-red-500 to-red-600' : 'bg-slate-700'}`} />

          {/* Icon Background Decoration */}
          <div className="absolute -right-4 -bottom-4 opacity-5 group-hover:opacity-10 transition-opacity">
            <AlertCircle className="h-32 w-32" aria-hidden="true" />
          </div>

          {/* Content */}
          <div className="relative z-10">
            {/* Header */}
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-lg ${errorCount > 0 ? 'bg-red-500/10 border border-red-500/20' : 'bg-slate-800 border border-slate-700'}`}>
                <AlertCircle className={`h-5 w-5 ${errorCount > 0 ? 'text-red-400' : 'text-slate-400'}`} aria-hidden="true" />
              </div>
              {errorCount === 0 && (
                <div className="flex items-center gap-1 text-xs px-2 py-1 rounded-full bg-emerald-500/10 text-emerald-400">
                  <span className="font-semibold">✓ Clean</span>
                </div>
              )}
            </div>

            {/* Title */}
            <h3 className="text-xs font-medium text-slate-400 uppercase tracking-wide mb-2">
              Erreurs
            </h3>

            {/* Value */}
            <div className={`text-3xl font-bold mb-1 ${errorCount > 0 ? 'text-red-400' : 'text-emerald-400'}`}>
              {errorCount}
            </div>

            {/* Subtitle */}
            <p className="text-xs text-slate-500">
              {errorCount === 0 ? 'Aucune erreur détectée' : 'Erreurs dans l\'historique'}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
