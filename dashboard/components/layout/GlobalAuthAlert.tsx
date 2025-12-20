"use client"

import { AlertCircle } from "lucide-react"
import { useEffect, useState } from "react"
import { getSystemHealth } from "@/lib/api"
import Link from "next/link"

export function GlobalAuthAlert() {
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(true)
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
    const checkAuth = async () => {
      try {
        const health = await getSystemHealth()
        // If auth is NOT available, show alert
        if (health && health.auth_available === false) {
          setShow(true)
        } else {
            setShow(false)
        }
      } catch (e) {
      } finally {
        setLoading(false)
      }
    }

    checkAuth()
    const interval = setInterval(checkAuth, 60000) // Check every minute
    return () => clearInterval(interval)
  }, [])

  if (!mounted || loading || !show) return null

  return (
    <div className="w-full bg-destructive/15 border-b border-destructive/20 p-2">
      <div className="container mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
            <AlertCircle className="h-5 w-5 text-destructive" />
            <span className="text-sm font-medium text-destructive">
                Attention : Session LinkedIn expirée ou absente. Le bot ne peut pas fonctionner.
            </span>
        </div>
        <Link href="/auth" className="text-xs bg-destructive text-destructive-foreground px-3 py-1.5 rounded-md hover:bg-destructive/90 font-bold transition-colors">
            Réparer maintenant →
        </Link>
      </div>
    </div>
  )
}
