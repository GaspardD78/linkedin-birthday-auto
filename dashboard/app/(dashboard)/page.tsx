import { SystemHealthWidget } from "@/components/dashboard/HealthWidget"
import { LogsWidget } from "@/components/dashboard/LogsWidget"
import { BotControlsWidget } from "@/components/dashboard/BotControls"

export default function DashboardPage() {
  return (
    <div className="space-y-6 p-8 bg-slate-950 min-h-screen">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">
            🎯 Mission Control - LinkedIn Bot
          </h1>
          <p className="text-slate-500 text-sm mt-1">
            Console de Pilotage Raspberry Pi 4
          </p>
        </div>
        <div className="text-sm text-slate-500 flex items-center gap-2">
          <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          v2.0.0
        </div>
      </div>

      {/* Main Grid Layout */}
      <div className="grid gap-6">

        {/* Haut: System Health */}
        <div className="w-full">
          <SystemHealthWidget />
        </div>

        {/* Milieu: Task Runner */}
        <div className="w-full">
          <BotControlsWidget />
        </div>

        {/* Bas: Logs Console (grande zone) */}
        <div className="w-full min-h-[500px]">
          <LogsWidget />
        </div>

      </div>

      {/* Footer Info */}
      <div className="text-center text-xs text-slate-700 pt-4 border-t border-slate-800">
        <p>LinkedIn Bot Dashboard v2 - Powered by Next.js & Python 🚀</p>
      </div>
    </div>
  )
}
