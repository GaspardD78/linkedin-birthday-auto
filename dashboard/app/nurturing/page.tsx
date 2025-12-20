"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Bell,
  Users,
  Target,
  Briefcase,
  UserPlus,
  Clock,
  AlertTriangle,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  TrendingUp
} from "lucide-react"

interface Segment {
  type: string
  name: string
  description: string
  count: number
  priority: string
}

interface Alert {
  type: string
  priority: string
  title: string
  message: string
  contacts_count: number
  action_url: string | null
}

interface ContactSegment {
  name: string
  linkedin_url: string | null
  last_contact_date: string | null
  message_count: number
  fit_score: number | null
  days_since_contact: number | null
  segment_reason: string
}

interface SegmentDetail {
  segment_type: string
  segment_name: string
  description: string
  contacts: ContactSegment[]
  total: number
  criteria: Record<string, unknown>
}

export default function NurturingPage() {
  const [segments, setSegments] = useState<Segment[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Segment detail dialog
  const [selectedSegment, setSelectedSegment] = useState<SegmentDetail | null>(null)
  const [loadingSegment, setLoadingSegment] = useState(false)

  // Chargement des segments et alertes
  const loadData = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const [segmentsRes, alertsRes] = await Promise.all([
        fetch("/api/nurturing"),
        fetch("/api/nurturing/alerts")
      ])

      if (segmentsRes.ok) {
        const segmentsData = await segmentsRes.json()
        setSegments(segmentsData.segments || [])
      }

      if (alertsRes.ok) {
        const alertsData = await alertsRes.json()
        setAlerts(alertsData.alerts || [])
      }

    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement")
    } finally {
      setLoading(false)
    }
  }, [])

  // Chargement d&apos;un segment
  const loadSegmentDetail = async (segmentType: string) => {
    setLoadingSegment(true)
    try {
      const res = await fetch(`/api/nurturing/segments/${segmentType}?limit=50`)
      if (res.ok) {
        const data = await res.json()
        setSelectedSegment(data)
      }
    } catch (err) {
    } finally {
      setLoadingSegment(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [loadData])

  // Icône selon le type de segment
  const getSegmentIcon = (type: string) => {
    switch (type) {
      case "inactive_contacts": return <Clock className="h-5 w-5 text-orange-400" />
      case "high_score_profiles": return <Target className="h-5 w-5 text-emerald-400" />
      case "open_to_work": return <Briefcase className="h-5 w-5 text-blue-400" />
      case "new_connections": return <UserPlus className="h-5 w-5 text-purple-400" />
      default: return <Users className="h-5 w-5 text-slate-400" />
    }
  }

  // Couleur de priorité
  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case "high": return <Badge className="bg-red-500">Haute</Badge>
      case "medium": return <Badge className="bg-yellow-500">Moyenne</Badge>
      case "low": return <Badge variant="outline">Basse</Badge>
      default: return <Badge variant="outline">{priority}</Badge>
    }
  }

  // Format date relatif
  const formatRelativeDate = (dateStr: string | null) => {
    if (!dateStr) return "-"
    const date = new Date(dateStr)
    const now = new Date()
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24))

    if (diffDays === 0) return "Aujourd&apos;hui"
    if (diffDays === 1) return "Hier"
    if (diffDays < 7) return `Il y a ${diffDays} jours`
    if (diffDays < 30) return `Il y a ${Math.floor(diffDays / 7)} semaine(s)`
    return `Il y a ${Math.floor(diffDays / 30)} mois`
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Nurturing</h1>
          <p className="text-slate-400">Segments et alertes pour le suivi de vos contacts</p>
        </div>
        <Button variant="ghost" size="icon" onClick={loadData}>
          <RefreshCw className={`h-5 w-5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
        </div>
      )}

      {/* Alertes */}
      {alerts.length > 0 && (
        <Card className="bg-gradient-to-r from-orange-900/20 to-red-900/20 border-orange-500/30">
          <CardHeader>
            <CardTitle className="text-white flex items-center gap-2">
              <Bell className="h-5 w-5 text-orange-400" />
              Alertes ({alerts.length})
            </CardTitle>
            <CardDescription>Actions prioritaires recommandées</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {alerts.map((alert, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between bg-slate-900/50 rounded-lg p-4 border border-slate-800"
              >
                <div className="flex items-center gap-4">
                  <div className={`p-2 rounded-lg ${
                    alert.priority === "high" ? "bg-red-500/20" : "bg-yellow-500/20"
                  }`}>
                    <AlertTriangle className={`h-5 w-5 ${
                      alert.priority === "high" ? "text-red-400" : "text-yellow-400"
                    }`} />
                  </div>
                  <div>
                    <p className="text-white font-medium">{alert.title}</p>
                    <p className="text-sm text-slate-400">{alert.message}</p>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {getPriorityBadge(alert.priority)}
                  {alert.action_url && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => window.location.href = alert.action_url!}
                    >
                      Voir <ChevronRight className="h-4 w-4 ml-1" />
                    </Button>
                  )}
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      )}

      {/* Segments */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {loading ? (
          <div className="col-span-2 text-center py-8 text-slate-400">Chargement...</div>
        ) : segments.length === 0 ? (
          <div className="col-span-2 text-center py-8 text-slate-400">Aucun segment disponible</div>
        ) : (
          segments.map((segment) => (
            <Card
              key={segment.type}
              className="bg-slate-900 border-slate-800 hover:border-slate-700 transition-all cursor-pointer"
              onClick={() => loadSegmentDetail(segment.type)}
            >
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-slate-800 rounded-lg">
                      {getSegmentIcon(segment.type)}
                    </div>
                    <div>
                      <h3 className="text-white font-semibold">{segment.name}</h3>
                      <p className="text-sm text-slate-400">{segment.description}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-2xl font-bold text-white">{segment.count}</p>
                    {getPriorityBadge(segment.priority)}
                  </div>
                </div>
                <div className="mt-4 flex justify-end">
                  <Button variant="ghost" size="sm" className="text-blue-400">
                    Voir le segment <ChevronRight className="h-4 w-4 ml-1" />
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Tips Card */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-emerald-400" />
            Conseils Nurturing
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
            <div className="bg-slate-800 p-4 rounded-lg">
              <h4 className="text-emerald-400 font-medium mb-2">Contacts inactifs</h4>
              <p className="text-slate-400">
                Réactivez les contacts dormants avec un message d&apos;anniversaire ou une visite de profil.
              </p>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg">
              <h4 className="text-blue-400 font-medium mb-2">Profils qualifiés</h4>
              <p className="text-slate-400">
                Les profils avec un score élevé sont des candidats prioritaires pour le sourcing.
              </p>
            </div>
            <div className="bg-slate-800 p-4 rounded-lg">
              <h4 className="text-purple-400 font-medium mb-2">Open to Work</h4>
              <p className="text-slate-400">
                Les candidats disponibles sont plus réceptifs aux propositions.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Segment Detail Dialog */}
      <Dialog open={!!selectedSegment} onOpenChange={() => setSelectedSegment(null)}>
        <DialogContent className="bg-slate-900 border-slate-800 max-w-3xl max-h-[80vh] overflow-y-auto">
          {loadingSegment ? (
            <div className="text-center py-8 text-slate-400">Chargement...</div>
          ) : selectedSegment && (
            <>
              <DialogHeader>
                <DialogTitle className="text-white text-xl flex items-center gap-2">
                  {getSegmentIcon(selectedSegment.segment_type)}
                  {selectedSegment.segment_name}
                </DialogTitle>
                <DialogDescription>
                  {selectedSegment.description} - {selectedSegment.total} contacts
                </DialogDescription>
              </DialogHeader>

              <div className="mt-4">
                {selectedSegment.contacts.length === 0 ? (
                  <div className="text-center py-8 text-slate-400">
                    Aucun contact dans ce segment
                  </div>
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow className="border-slate-800">
                        <TableHead className="text-slate-400">Nom</TableHead>
                        <TableHead className="text-slate-400">Raison</TableHead>
                        <TableHead className="text-slate-400">Dernier contact</TableHead>
                        <TableHead className="text-slate-400">Actions</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedSegment.contacts.map((contact, idx) => (
                        <TableRow key={idx} className="border-slate-800">
                          <TableCell className="font-medium text-white">
                            {contact.name}
                          </TableCell>
                          <TableCell className="text-slate-400 text-sm max-w-[200px] truncate">
                            {contact.segment_reason}
                          </TableCell>
                          <TableCell className="text-slate-300">
                            {contact.days_since_contact !== null
                              ? `${contact.days_since_contact} jours`
                              : formatRelativeDate(contact.last_contact_date)}
                          </TableCell>
                          <TableCell>
                            {contact.linkedin_url && (
                              <Button
                                variant="ghost"
                                size="icon"
                                onClick={() => window.open(contact.linkedin_url!, "_blank")}
                              >
                                <ExternalLink className="h-4 w-4 text-blue-400" />
                              </Button>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
