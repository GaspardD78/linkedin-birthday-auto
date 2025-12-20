"use client"

import { useEffect, useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Clock,
  Database,
  Trash2,
  Server,
  Power,
  PowerOff,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RefreshCw
} from "lucide-react"
import { useToast } from "@/components/ui/use-toast"
import { getAutomationServicesStatus, executeServiceAction } from "@/lib/api"

interface ServiceStatus {
  name: string
  display_name: string
  active: boolean
  enabled: boolean
  status: string
  description: string
}

interface ServicesStatusResponse {
  services: ServiceStatus[]
  is_systemd_available: boolean
}

export function AutomationServicesControl() {
  const [status, setStatus] = useState<ServicesStatusResponse | null>(null)
  const [loading, setLoading] = useState<string | null>(null)
  const { toast } = useToast()

  const refreshStatus = async () => {
    try {
      const data = await getAutomationServicesStatus()
      setStatus(data)
    } catch (error) {
    }
  }

  useEffect(() => {
    refreshStatus()
    const interval = setInterval(refreshStatus, 10000) // Refresh every 10 seconds
    return () => clearInterval(interval)
  }, [])

  const handleServiceAction = async (serviceName: string, action: string) => {
    const actionKey = `${serviceName}-${action}`
    setLoading(actionKey)
    try {
      await executeServiceAction(serviceName, action)
      toast({
        title: "Action exécutée",
        description: `${action} effectué sur ${serviceName}`,
      })
      // Wait a bit for systemd to process the action, then refresh
      setTimeout(refreshStatus, 1500)
    } catch (error: any) {
      toast({
        variant: "destructive",
        title: "Erreur",
        description: error.message
      })
    } finally {
      setLoading(null)
    }
  }

  if (!status) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Server className="h-5 w-5 text-purple-500" />
            Services d&apos;Automatisation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-slate-400" />
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!status.is_systemd_available && status.services.length === 0) {
    return (
      <Card className="w-full bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-slate-200">
            <Server className="h-5 w-5 text-purple-500" />
            Services d&apos;Automatisation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-start gap-3 p-4 rounded-lg bg-blue-500/10 border border-blue-500/30">
            <AlertTriangle className="h-5 w-5 text-blue-400 flex-shrink-0 mt-0.5" />
            <div>
              <h4 className="text-sm font-semibold text-blue-300 mb-1">
                Mode Docker détecté
              </h4>
              <p className="text-xs text-blue-200/80">
                Les services d&apos;automatisation sont gérés par RQ Workers dans Docker.
                Aucun worker actif n&apos;a été détecté. Vérifiez que le service worker est démarré.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getServiceIcon = (name: string) => {
    // RQ Worker services (Docker mode)
    if (name.startsWith("rq_worker")) return Server
    if (name === "rq_queue") return Clock

    // Systemd services (Raspberry Pi mode)
    switch (name) {
      case "monitor":
        return Clock
      case "backup":
        return Database
      case "cleanup":
        return Trash2
      case "main":
        return Server
      default:
        return Server
    }
  }

  const getServiceColor = (name: string) => {
    // RQ Worker services (Docker mode)
    if (name.startsWith("rq_worker")) return "green"
    if (name === "rq_queue") return "blue"

    // Systemd services (Raspberry Pi mode)
    switch (name) {
      case "monitor":
        return "purple"
      case "backup":
        return "blue"
      case "cleanup":
        return "orange"
      case "main":
        return "green"
      default:
        return "slate"
    }
  }

  const ServiceCard = ({ service }: { service: ServiceStatus }) => {
    const Icon = getServiceIcon(service.name)
    const color = getServiceColor(service.name)

    const colorClasses = {
      purple: {
        card: 'bg-gradient-to-br from-purple-900/20 to-slate-900 border-purple-700/40',
        icon: service.active ? 'bg-purple-500/20' : 'bg-slate-800/50',
        iconColor: service.active ? 'text-purple-400' : 'text-slate-400',
        badge: service.active ? 'bg-purple-600' : 'bg-slate-700'
      },
      blue: {
        card: 'bg-gradient-to-br from-blue-900/20 to-slate-900 border-blue-700/40',
        icon: service.active ? 'bg-blue-500/20' : 'bg-slate-800/50',
        iconColor: service.active ? 'text-blue-400' : 'text-slate-400',
        badge: service.active ? 'bg-blue-600' : 'bg-slate-700'
      },
      orange: {
        card: 'bg-gradient-to-br from-orange-900/20 to-slate-900 border-orange-700/40',
        icon: service.active ? 'bg-orange-500/20' : 'bg-slate-800/50',
        iconColor: service.active ? 'text-orange-400' : 'text-slate-400',
        badge: service.active ? 'bg-orange-600' : 'bg-slate-700'
      },
      green: {
        card: 'bg-gradient-to-br from-green-900/20 to-slate-900 border-green-700/40',
        icon: service.active ? 'bg-green-500/20' : 'bg-slate-800/50',
        iconColor: service.active ? 'text-green-400' : 'text-slate-400',
        badge: service.active ? 'bg-green-600' : 'bg-slate-700'
      },
      slate: {
        card: 'bg-slate-900 border-slate-700',
        icon: 'bg-slate-800/50',
        iconColor: 'text-slate-400',
        badge: 'bg-slate-700'
      }
    }[color]

    const startKey = `${service.name}-start`
    const stopKey = `${service.name}-stop`
    const enableKey = `${service.name}-enable`
    const disableKey = `${service.name}-disable`

    return (
      <Card className={`${colorClasses.card} transition-all duration-300`}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className={`p-2 rounded-full ${colorClasses.icon}`}>
                <Icon className={`h-4 w-4 ${colorClasses.iconColor}`} />
              </div>
              <div>
                <CardTitle className="text-sm text-slate-200">
                  {service.display_name}
                </CardTitle>
                <CardDescription className="text-xs mt-0.5">
                  {service.description}
                </CardDescription>
              </div>
            </div>
            <div className="flex flex-col items-end gap-1">
              <Badge
                variant={service.active ? "default" : "secondary"}
                className={`${colorClasses.badge} text-xs`}
              >
                {service.active ? "Actif" : "Inactif"}
              </Badge>
              {service.enabled ? (
                <div className="flex items-center gap-1 text-xs text-emerald-400">
                  <CheckCircle className="h-3 w-3" />
                  <span>Auto</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 text-xs text-slate-500">
                  <XCircle className="h-3 w-3" />
                  <span>Manuel</span>
                </div>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-2">
          {/* Only show control buttons for systemd services, not for RQ workers in Docker */}
          {!service.name.startsWith("rq_") ? (
            <div className="grid grid-cols-2 gap-2">
              {service.active ? (
                <Button
                  variant="destructive"
                  size="sm"
                  onClick={() => handleServiceAction(service.name, "stop")}
                  disabled={loading === stopKey}
                  className="text-xs"
                >
                  {loading === stopKey ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <PowerOff className="h-3 w-3 mr-1" />
                  )}
                  Arrêter
                </Button>
              ) : (
                <Button
                  variant="default"
                  size="sm"
                  onClick={() => handleServiceAction(service.name, "start")}
                  disabled={loading === startKey}
                  className="text-xs bg-emerald-600 hover:bg-emerald-700"
                >
                  {loading === startKey ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <Power className="h-3 w-3 mr-1" />
                  )}
                  Démarrer
                </Button>
              )}

              {service.enabled ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleServiceAction(service.name, "disable")}
                  disabled={loading === disableKey}
                  className="text-xs border-slate-700"
                >
                  {loading === disableKey ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <XCircle className="h-3 w-3 mr-1" />
                  )}
                  Désactiver
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleServiceAction(service.name, "enable")}
                  disabled={loading === enableKey}
                  className="text-xs border-slate-700"
                >
                  {loading === enableKey ? (
                    <RefreshCw className="h-3 w-3 mr-1 animate-spin" />
                  ) : (
                    <CheckCircle className="h-3 w-3 mr-1" />
                  )}
                  Activer
                </Button>
              )}
            </div>
          ) : (
            <div className="text-xs text-slate-400 text-center py-2">
              Géré par Docker Compose
            </div>
          )}
        </CardContent>
      </Card>
    )
  }

  // Determine mode-specific display text
  const isDockerMode = !status.is_systemd_available
  const title = isDockerMode ? "Workers d&apos;Automatisation (Docker)" : "Services d&apos;Automatisation"
  const description = isDockerMode
    ? "Workers RQ pour tâches asynchrones (birthday messages, profile visits)"
    : "Gestion des services systemd (monitoring, backup, cleanup)"

  return (
    <Card className="w-full bg-slate-900 border-slate-800">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-slate-200">
              <Server className="h-5 w-5 text-purple-500" />
              {title}
            </CardTitle>
            <CardDescription className="mt-1">
              {description}
            </CardDescription>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={refreshStatus}
            className="border-slate-700"
          >
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {status.services.map((service) => (
            <ServiceCard key={service.name} service={service} />
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
