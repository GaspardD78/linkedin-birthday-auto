import { SystemHealthWidget } from "@/components/dashboard/HealthWidget"
import { BotStatusWidget } from "@/components/dashboard/BotStatus"
import { LogsWidget } from "@/components/dashboard/LogsWidget"
import { BotControlsWidget } from "@/components/dashboard/BotControls"
import { StatsWidget } from "@/components/dashboard/StatsWidget"

export default function DashboardPage() {
  return (
    <div className="space-y-8 p-8 bg-slate-950 min-h-screen">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-white tracking-tight">LinkedIn Bot Dashboard</h1>
        <div className="text-sm text-slate-500">v2.0.0</div>
      </div>

      {/* Top Stats Row */}
      <StatsWidget />

      {/* Main Content Grid */}
      <div className="grid gap-4 md:grid-cols-12">

        {/* Left Column: Status & Controls (4 cols) */}
        <div className="md:col-span-4 space-y-4">
          <BotStatusWidget />
          <SystemHealthWidget />
          <BotControlsWidget />
        </div>

        {/* Right Column: Logs & Activity (8 cols) */}
        <div className="md:col-span-8 space-y-4">
           {/* We can add an Activity Graph here later */}
           <LogsWidget />
        </div>
      </div>
    </div>
  )
}
