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
import { DashboardHeader } from "@/components/dashboard/DashboardHeader"

export default function DashboardPage() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 p-4 lg:p-6">
      <div className="max-w-[1920px] mx-auto space-y-6">
        {/* Enhanced Header */}
        <DashboardHeader />

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
        <div className="text-center text-xs text-slate-700 pt-6 border-t border-slate-800/50">
          <p className="flex items-center justify-center gap-2">
            <span>LinkedIn Bot Dashboard v2</span>
            <span className="text-slate-800">•</span>
            <span>Powered by Next.js & Python</span>
            <span className="text-emerald-500">🚀</span>
          </p>
        </div>
      </div>
    </div>
  )
}
