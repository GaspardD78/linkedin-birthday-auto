import { SystemHealthWidget } from "@/components/dashboard/HealthWidget"
import { LogsWidget } from "@/components/dashboard/LogsWidget"
import { BotControlsWidget } from "@/components/dashboard/BotControls"
import { EnhancedStatsWidget } from "@/components/dashboard/EnhancedStatsWidget"
import { WeeklyLimitWidget } from "@/components/dashboard/WeeklyLimitWidget"
import { TopContactsWidget } from "@/components/dashboard/TopContactsWidget"
import { ActivityChartWidget } from "@/components/dashboard/ActivityChartWidget"
import { RecentErrorsWidget } from "@/components/dashboard/RecentErrorsWidget"
import { BotStatusWidget } from "@/components/dashboard/BotStatus"
import { DeploymentWidget } from "@/components/dashboard/DeploymentWidget"

export default function DashboardPage() {
  return (
    <div className="space-y-5 bg-slate-950 min-h-screen w-full max-w-[1920px] mx-auto">
      {/* Header */}
      <div className="flex justify-between items-center mb-1">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            Dashboard - LinkedIn Birthday Auto
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Console de pilotage et monitoring en temps réel
          </p>
        </div>
        <div className="text-sm text-slate-500 flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 pulse-glow" />
          <span className="font-mono">v2.0.0</span>
        </div>
      </div>

      {/* Statistics Cards - 4 columns like V1 */}
      <EnhancedStatsWidget />

      {/* Weekly Limit Progress Bar */}
      <WeeklyLimitWidget />

      {/* Main Grid Layout - 2 columns like V1 (8/12 + 4/12) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

        {/* Left Column (8/12) - Activity Chart + Logs */}
        <div className="lg:col-span-8 space-y-5">

          {/* Activity Chart */}
          <ActivityChartWidget />

          {/* Logs Console */}
          <div className="min-h-[400px]">
            <LogsWidget />
          </div>

        </div>

        {/* Right Column (4/12) - Controls + Weekly Limit + Contacts + Errors */}
        <div className="lg:col-span-4 space-y-5">

          {/* Bot Controls */}
          <BotControlsWidget />

          {/* Bot Status */}
          <BotStatusWidget />

          {/* System Health */}
          <SystemHealthWidget />

          {/* Deployment & Maintenance */}
          <DeploymentWidget />

          {/* Top 5 Contacts */}
          <TopContactsWidget />

          {/* Recent Errors */}
          <RecentErrorsWidget />

        </div>

      </div>

      {/* Footer Info */}
      <div className="text-center text-xs text-slate-700 pt-4 border-t border-slate-800">
        <p>LinkedIn Bot Dashboard v2 - Powered by Next.js & Python 🚀</p>
      </div>
    </div>
  )
}
