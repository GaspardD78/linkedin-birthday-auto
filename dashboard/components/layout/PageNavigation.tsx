"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { ChevronLeft, Home, Settings, History, Terminal, KeyRound } from "lucide-react"
import { Button } from "@/components/ui/button"

interface PageNavigationProps {
  title: string
  description?: string
  showBackButton?: boolean
}

const navigationItems = [
  { href: "/", icon: Home, label: "Tableau de bord" },
  { href: "/history", icon: History, label: "Historique" },
  { href: "/logs", icon: Terminal, label: "Logs" },
  { href: "/auth", icon: KeyRound, label: "Auth" },
  { href: "/settings", icon: Settings, label: "Paramètres" },
]

export function PageNavigation({ title, description, showBackButton = false }: PageNavigationProps) {
  const pathname = usePathname()

  return (
    <div className="mb-6">
      {/* Breadcrumb / Back button */}
      {showBackButton && (
        <Link href="/" className="inline-flex items-center text-sm text-slate-400 hover:text-white mb-3 transition-colors">
          <ChevronLeft className="h-4 w-4 mr-1" />
          Retour au tableau de bord
        </Link>
      )}

      {/* Page title */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-3xl font-bold text-white">{title}</h1>
          {description && <p className="text-slate-400 mt-1">{description}</p>}
        </div>
      </div>

      {/* Quick navigation tabs */}
      <div className="flex flex-wrap gap-2 border-b border-slate-800 pb-3">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href
          return (
            <Link key={item.href} href={item.href}>
              <Button
                variant={isActive ? "default" : "ghost"}
                size="sm"
                className={`
                  ${isActive
                    ? "bg-blue-600 text-white hover:bg-blue-700"
                    : "text-slate-400 hover:text-white hover:bg-slate-800"
                  }
                `}
              >
                <item.icon className="h-4 w-4 mr-2" />
                {item.label}
              </Button>
            </Link>
          )
        })}
      </div>
    </div>
  )
}
