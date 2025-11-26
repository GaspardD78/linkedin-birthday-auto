import Link from "next/link"
import {
  LayoutDashboard,
  Settings,
  Activity,
  Terminal,
  KeyRound
} from "lucide-react"

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Pilotage" },
  { href: "/logs", icon: Terminal, label: "Logs & Console" },
  { href: "/auth", icon: KeyRound, label: "Authentification" },
  { href: "/settings", icon: Settings, label: "Paramètres" },
]

export function Sidebar() {
  return (
    <div className="flex h-full flex-col gap-4 py-6">
      <div className="px-6 flex items-center gap-2 font-bold text-xl text-blue-400">
        <Activity className="h-6 w-6" />
        <span>LinkedIn Bot</span>
      </div>

      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-slate-300 transition-all hover:text-white hover:bg-slate-800"
          >
            <item.icon className="h-5 w-5" />
            <span>{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="px-6 mt-auto">
        <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
          <p className="text-xs text-slate-500 font-mono">System Status</p>
          <div className="mt-2 flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-sm text-emerald-400">Online</span>
          </div>
        </div>
      </div>
    </div>
  )
}
