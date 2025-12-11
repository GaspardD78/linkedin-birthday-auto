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
  UserX,
  Target
} from "lucide-react"

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Tableau de Bord", description: "Pilotage & monitoring" },
  { href: "/sourcing", icon: Target, label: "Sourcing", description: "Recherche & export profils" },
  { href: "/history", icon: History, label: "Historique", description: "Détails des exécutions" },
  { href: "/blacklist", icon: UserX, label: "Blacklist", description: "Contacts exclus" },
  { href: "/logs", icon: Terminal, label: "Logs", description: "Console en temps réel" },
  { href: "/auth", icon: KeyRound, label: "Authentification", description: "Cookies LinkedIn" },
  { href: "/settings", icon: Settings, label: "Paramètres", description: "Configuration" },
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

      <nav className="flex-1 px-4 space-y-1 mt-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`group flex flex-col rounded-lg px-3 py-2.5 transition-all ${
                isActive
                  ? "bg-gradient-to-r from-blue-600/20 to-cyan-600/20 border-l-4 border-blue-500 text-white font-medium shadow-lg shadow-blue-500/10"
                  : "text-slate-300 hover:text-white hover:bg-slate-800/50 border-l-4 border-transparent"
              }`}
            >
              <div className="flex items-center gap-3">
                <item.icon className={`h-5 w-5 ${isActive ? "text-blue-400" : "text-slate-400 group-hover:text-slate-200"}`} />
                <span>{item.label}</span>
              </div>
              <span className="text-xs text-slate-500 ml-8 mt-0.5">{item.description}</span>
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
