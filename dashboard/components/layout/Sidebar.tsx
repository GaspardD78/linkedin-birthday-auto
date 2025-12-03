"use client"

import Link from "next/link"
import { usePathname, useRouter } from "next/navigation"
import {
  LayoutDashboard,
  Settings,
  Activity,
  Terminal,
  KeyRound,
  History,
  LogOut,
  Eye
} from "lucide-react"

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Pilotage" },
  { href: "/overview", icon: Eye, label: "Vue d'ensemble" },
  { href: "/history", icon: History, label: "Historique" },
  { href: "/logs", icon: Terminal, label: "Logs & Console" },
  { href: "/auth", icon: KeyRound, label: "Authentification" },
  { href: "/settings", icon: Settings, label: "Paramètres" },
]

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()

  const handleLogout = async () => {
    try {
      await fetch("/api/auth/logout", { method: "POST" })
      router.push("/login")
      router.refresh()
    } catch (error) {
      console.error("Logout failed", error)
    }
  }

  return (
    <div className="flex h-full flex-col gap-4 py-6">
      <div className="px-6 flex items-center gap-2 font-bold text-xl text-blue-400">
        <Activity className="h-6 w-6" />
        <span>LinkedIn Bot</span>
      </div>

      <nav className="flex-1 px-4 space-y-2 mt-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 transition-all ${
                isActive
                  ? "bg-slate-800 text-white font-medium"
                  : "text-slate-300 hover:text-white hover:bg-slate-800"
              }`}
            >
              <item.icon className="h-5 w-5" />
              <span>{item.label}</span>
            </Link>
          )
        })}
      </nav>

      <div className="px-4 mt-auto space-y-4">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-red-400 hover:bg-red-950/30 hover:text-red-300 transition-all"
        >
          <LogOut className="h-5 w-5" />
          <span>Déconnexion</span>
        </button>

        <div className="px-2">
          <div className="rounded-lg bg-slate-900 p-4 border border-slate-800">
            <p className="text-xs text-slate-500 font-mono">System Status</p>
            <div className="mt-2 flex items-center gap-2">
              <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-sm text-emerald-400">Online</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
