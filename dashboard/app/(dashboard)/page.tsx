import { SystemHealthWidget } from "@/components/dashboard/HealthWidget"
import { TaskStatusWidget } from "@/components/dashboard/TaskStatusWidget"
import { BotControlsWidget } from "@/components/dashboard/BotControls"
import { EnhancedStatsWidget } from "@/components/dashboard/EnhancedStatsWidget"
import { WeeklyLimitWidget } from "@/components/dashboard/WeeklyLimitWidget"
import { TopContactsWidget } from "@/components/dashboard/TopContactsWidget"
import { ActivityChartWidget } from "@/components/dashboard/ActivityChartWidget"
import { RecentErrorsWidget } from "@/components/dashboard/RecentErrorsWidget"
import { BotStatusWidget } from "@/components/dashboard/BotStatus"
import { DeploymentWidget } from "@/components/dashboard/DeploymentWidget"
import { DashboardHeader } from "@/components/dashboard/DashboardHeader"
import { PilotageOverview } from "@/components/dashboard/PilotageOverview"

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 lg:p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">

        {/* Hero Section - Vue d'ensemble Pilotage */}
        <PilotageOverview />

        {/* Main Control & Monitoring Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Zone de Contrôle Principale (8/12) */}
          <div className="lg:col-span-8 space-y-6">

            {/* Contrôle des Scripts - Mise en avant */}
            <BotControlsWidget />

            {/* Statistics Cards */}
            <EnhancedStatsWidget />

            {/* Weekly Limit Progress Bar */}
            <WeeklyLimitWidget />

            {/* Activity Chart */}
            <ActivityChartWidget />

          </div>

          {/* Panneau de Monitoring (4/12) */}
          <div className="lg:col-span-4 space-y-6">

            {/* Activité en temps réel (Logs Light) */}
            <TaskStatusWidget />

            {/* État des Workers - Détails */}
            <BotStatusWidget />

            {/* Santé Système - Détails */}
            <SystemHealthWidget />

            {/* Déploiement & Maintenance */}
            <DeploymentWidget />

            {/* Top 5 Contacts */}
            <TopContactsWidget />

            {/* Recent Errors */}
            <RecentErrorsWidget />

          </div>

        </div>

        {/* Footer Info */}
        <div className="text-center text-xs text-slate-700 pt-6 border-t border-slate-800/50">
          <p className="flex items-center justify-center gap-2">
            <span>LinkedIn Bot Dashboard v2 - Pilotage</span>
            <span className="text-slate-800">•</span>
            <span>Powered by Next.js & Python</span>
            <span className="text-emerald-500">🚀</span>
          </p>
        </div>
      </div>
    </div>
  )
}
