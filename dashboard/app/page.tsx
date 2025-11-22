import { SystemHealthWidget } from "@/components/dashboard/HealthWidget"
import { BotStatusWidget } from "@/components/dashboard/BotStatus"

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      <h1 className="text-3xl font-bold text-white">Vue d'ensemble</h1>

      {/* KPIs & Status Row */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <BotStatusWidget />
        <SystemHealthWidget />

        {/* Placeholder Stat Card */}
        <div className="p-6 rounded-xl bg-slate-900 border border-slate-800">
           <h3 className="text-sm font-medium text-slate-200 mb-2">Messages envoyés (24h)</h3>
           <div className="text-2xl font-bold text-white">0</div>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
         <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 h-96 flex items-center justify-center text-slate-600">
           Graphique Activité (Placeholder)
         </div>
         <div className="p-6 rounded-xl bg-slate-900 border border-slate-800 h-96 flex items-center justify-center text-slate-600">
           Logs Récents (Placeholder)
         </div>
      </div>
    </div>
  )
}
