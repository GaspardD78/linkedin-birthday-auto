import { SystemStatusHero } from "@/components/dashboard/SystemStatusHero"
import { BotControlPanel } from "@/components/dashboard/BotControlPanel"
import { KPICards } from "@/components/dashboard/KPICards"
import { ActivityMonitor } from "@/components/dashboard/ActivityMonitor"
import { WeeklyLimitWidget } from "@/components/dashboard/WeeklyLimitWidget"
import { TopContactsWidget } from "@/components/dashboard/TopContactsWidget"
import { RecentErrorsWidget } from "@/components/dashboard/RecentErrorsWidget"

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950">
      <div className="max-w-[1920px] mx-auto space-y-6">

        {/* Page Title */}
        <div className="mb-6">
          <h1 className="text-4xl font-bold bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent mb-2">
            Tableau de Bord
          </h1>
          <p className="text-slate-400">
            Pilotage centralisé et monitoring en temps réel de LinkedIn Birthday Auto
          </p>
        </div>

        {/* Hero Section - System Status */}
        <SystemStatusHero />

        {/* Main Grid Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">

          {/* Left Column - Main Controls & Stats (8/12) */}
          <div className="lg:col-span-8 space-y-6">

            {/* Bot Control Panel */}
            <BotControlPanel />

            {/* KPI Cards */}
            <KPICards />

            {/* Weekly Limit Progress */}
            <WeeklyLimitWidget />

            {/* Activity Monitor with Tabs (Chart + Logs) */}
            <ActivityMonitor />

          </div>

          {/* Right Column - Sidebar Widgets (4/12) */}
          <div className="lg:col-span-4 space-y-6">

            {/* Top Contacts */}
            <TopContactsWidget />

            {/* Recent Errors */}
            <RecentErrorsWidget />

          </div>

        </div>

        {/* Footer */}
        <div className="text-center text-xs text-slate-700 pt-6 pb-4 border-t border-slate-800/50">
          <p className="flex items-center justify-center gap-2">
            <span>LinkedIn Birthday Auto v2.0</span>
            <span className="text-slate-800">•</span>
            <span>Dashboard Redesign</span>
            <span className="text-slate-800">•</span>
            <span>Powered by Next.js & Python</span>
          </p>
        </div>
      </div>
    </div>
  )
}
