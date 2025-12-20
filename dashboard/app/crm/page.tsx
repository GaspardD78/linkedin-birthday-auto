"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
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
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import {
  Search,
  Users,
  MessageSquare,
  Calendar,
  TrendingUp,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  Clock,
  Gift,
  UserX
} from "lucide-react"

interface ContactSummary {
  id: number | null
  name: string
  linkedin_url: string | null
  message_count: number
  last_message_date: string | null
  first_contact_date: string | null
  relationship_score: number | null
  is_blacklisted: boolean
}

interface ContactMessage {
  id: number
  message_text: string
  sent_at: string
  is_late: boolean
  days_late: number
}

interface ContactDetail {
  id: number | null
  name: string
  linkedin_url: string | null
  message_count: number
  last_message_date: string | null
  relationship_score: number | null
  created_at: string | null
  messages: ContactMessage[]
  profile_visits: Array<{
    id: number
    visited_at: string
    success: boolean
  }>
  is_blacklisted: boolean
}

interface CRMStats {
  total_contacts: number
  total_messages_sent: number
  contacts_this_month: number
  messages_this_month: number
  avg_messages_per_contact: number
  top_contacted: Array<{ name: string; message_count: number; last_message: string }>
}

export default function CRMPage() {
  // États
  const [contacts, setContacts] = useState<ContactSummary[]>([])
  const [stats, setStats] = useState<CRMStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Pagination
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(25)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Recherche et tri
  const [search, setSearch] = useState("")
  const [sortBy, setSortBy] = useState("last_message_date")
  const [sortOrder, setSortOrder] = useState("desc")

  // Detail dialog
  const [selectedContact, setSelectedContact] = useState<ContactDetail | null>(null)
  const [loadingDetail, setLoadingDetail] = useState(false)

  // Chargement des stats
  const loadStats = useCallback(async () => {
    try {
      const res = await fetch("/api/crm/stats")
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
    }
  }, [])

  // Chargement des contacts
  const loadContacts = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        sort_by: sortBy,
        sort_order: sortOrder
      })

      if (search) {
        params.append("search", search)
      }

      const res = await fetch(`/api/crm?${params.toString()}`)

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()
      setContacts(data.contacts || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)

    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement")
      setContacts([])
    } finally {
      setLoading(false)
    }
  }, [page, perPage, sortBy, sortOrder, search])

  // Chargement du détail d&apos;un contact
  const loadContactDetail = async (contactName: string) => {
    setLoadingDetail(true)
    try {
      const res = await fetch(`/api/crm/contacts/${encodeURIComponent(contactName)}?years=5`)
      if (res.ok) {
        const data = await res.json()
        setSelectedContact(data)
      }
    } catch (err) {
    } finally {
      setLoadingDetail(false)
    }
  }

  useEffect(() => {
    loadStats()
  }, [loadStats])

  useEffect(() => {
    loadContacts()
  }, [loadContacts])

  // Recherche avec debounce
  const handleSearch = () => {
    setPage(1)
    loadContacts()
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
    if (diffDays < 365) return `Il y a ${Math.floor(diffDays / 30)} mois`
    return date.toLocaleDateString("fr-FR")
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">CRM - Relations</h1>
          <p className="text-slate-400">Historique des interactions avec vos contacts</p>
        </div>
      </div>

      {/* Stats Cards */}
      {stats && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/20 rounded-lg">
                  <Users className="h-5 w-5 text-blue-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total_contacts}</p>
                  <p className="text-xs text-slate-400">Contacts totaux</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <MessageSquare className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.total_messages_sent}</p>
                  <p className="text-xs text-slate-400">Messages envoyés</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <Calendar className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.messages_this_month}</p>
                  <p className="text-xs text-slate-400">Ce mois-ci</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/20 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.avg_messages_per_contact}</p>
                  <p className="text-xs text-slate-400">Msg/contact moyen</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Search Bar */}
      <Card className="bg-slate-900 border-slate-800">
        <CardContent className="p-4">
          <div className="flex items-center gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
              <Input
                placeholder="Rechercher un contact..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                className="pl-10 bg-slate-800 border-slate-700 text-white"
              />
            </div>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-[180px] bg-slate-800 border-slate-700">
                <SelectValue placeholder="Trier par" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="last_message_date">Dernier message</SelectItem>
                <SelectItem value="message_count">Nombre de messages</SelectItem>
                <SelectItem value="name">Nom</SelectItem>
                <SelectItem value="first_contact_date">Premier contact</SelectItem>
              </SelectContent>
            </Select>
            <Select value={sortOrder} onValueChange={setSortOrder}>
              <SelectTrigger className="w-[100px] bg-slate-800 border-slate-700">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="desc">Desc</SelectItem>
                <SelectItem value="asc">Asc</SelectItem>
              </SelectContent>
            </Select>
            <Button onClick={handleSearch} className="bg-blue-600 hover:bg-blue-700">
              <Search className="h-4 w-4 mr-2" />
              Rechercher
            </Button>
            <Button variant="ghost" size="icon" onClick={loadContacts}>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Contacts Table */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <CardTitle className="text-white">Contacts ({total})</CardTitle>
          <CardDescription>Cliquez sur un contact pour voir son historique complet</CardDescription>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8 text-red-400">{error}</div>
          ) : loading ? (
            <div className="text-center py-8 text-slate-400">Chargement...</div>
          ) : contacts.length === 0 ? (
            <div className="text-center py-8 text-slate-400">Aucun contact trouvé</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-800">
                    <TableHead className="text-slate-400">Nom</TableHead>
                    <TableHead className="text-slate-400">Messages</TableHead>
                    <TableHead className="text-slate-400">Dernier contact</TableHead>
                    <TableHead className="text-slate-400">Premier contact</TableHead>
                    <TableHead className="text-slate-400">Statut</TableHead>
                    <TableHead className="text-slate-400">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {contacts.map((contact, idx) => (
                    <TableRow
                      key={`${contact.name}-${idx}`}
                      className="border-slate-800 hover:bg-slate-800/50 cursor-pointer"
                      onClick={() => loadContactDetail(contact.name)}
                    >
                      <TableCell className="font-medium text-white">
                        <div className="flex items-center gap-2">
                          {contact.name}
                          {contact.is_blacklisted && (
                            <UserX className="h-4 w-4 text-red-400" title="Blacklisté" />
                          )}
                        </div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="secondary" className="bg-blue-500/20 text-blue-300">
                          {contact.message_count}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {formatRelativeDate(contact.last_message_date)}
                      </TableCell>
                      <TableCell className="text-slate-400 text-sm">
                        {contact.first_contact_date
                          ? new Date(contact.first_contact_date).toLocaleDateString("fr-FR")
                          : "-"}
                      </TableCell>
                      <TableCell>
                        {contact.is_blacklisted ? (
                          <Badge variant="destructive">Blacklisté</Badge>
                        ) : contact.message_count > 2 ? (
                          <Badge className="bg-emerald-500/20 text-emerald-300">Fidèle</Badge>
                        ) : (
                          <Badge variant="outline">Actif</Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {contact.linkedin_url && (
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={(e) => {
                              e.stopPropagation()
                              window.open(contact.linkedin_url!, "_blank")
                            }}
                          >
                            <ExternalLink className="h-4 w-4 text-blue-400" />
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-slate-400">
                  Page {page} sur {totalPages}
                </div>
                <div className="flex items-center gap-2">
                  <Select value={perPage.toString()} onValueChange={(v) => { setPerPage(parseInt(v)); setPage(1); }}>
                    <SelectTrigger className="w-[80px] bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="10">10</SelectItem>
                      <SelectItem value="25">25</SelectItem>
                      <SelectItem value="50">50</SelectItem>
                      <SelectItem value="100">100</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    <ChevronLeft className="h-4 w-4" />
                  </Button>
                  <Button
                    variant="outline"
                    size="icon"
                    disabled={page >= totalPages}
                    onClick={() => setPage(page + 1)}
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Contact Detail Dialog */}
      <Dialog open={!!selectedContact} onOpenChange={() => setSelectedContact(null)}>
        <DialogContent className="bg-slate-900 border-slate-800 max-w-2xl max-h-[80vh] overflow-y-auto">
          {loadingDetail ? (
            <div className="text-center py-8 text-slate-400">Chargement...</div>
          ) : selectedContact && (
            <>
              <DialogHeader>
                <DialogTitle className="text-white text-xl flex items-center gap-2">
                  {selectedContact.name}
                  {selectedContact.is_blacklisted && (
                    <Badge variant="destructive">Blacklisté</Badge>
                  )}
                </DialogTitle>
                <DialogDescription>
                  {selectedContact.message_count} messages envoyés
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-6 mt-4">
                {/* Stats rapides */}
                <div className="grid grid-cols-3 gap-4">
                  <div className="bg-slate-800 p-3 rounded-lg text-center">
                    <p className="text-2xl font-bold text-blue-400">{selectedContact.message_count}</p>
                    <p className="text-xs text-slate-400">Messages</p>
                  </div>
                  <div className="bg-slate-800 p-3 rounded-lg text-center">
                    <p className="text-2xl font-bold text-emerald-400">{selectedContact.profile_visits.length}</p>
                    <p className="text-xs text-slate-400">Visites profil</p>
                  </div>
                  <div className="bg-slate-800 p-3 rounded-lg text-center">
                    <p className="text-sm font-medium text-purple-400">
                      {formatRelativeDate(selectedContact.last_message_date)}
                    </p>
                    <p className="text-xs text-slate-400">Dernier contact</p>
                  </div>
                </div>

                {/* LinkedIn */}
                {selectedContact.linkedin_url && (
                  <Button
                    className="w-full bg-blue-600 hover:bg-blue-700"
                    onClick={() => window.open(selectedContact.linkedin_url!, "_blank")}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Voir le profil LinkedIn
                  </Button>
                )}

                {/* Historique des messages */}
                <div>
                  <h3 className="text-white font-semibold mb-3 flex items-center gap-2">
                    <Gift className="h-4 w-4 text-pink-400" />
                    Messages d&apos;anniversaire
                  </h3>
                  {selectedContact.messages.length === 0 ? (
                    <p className="text-slate-400 text-sm">Aucun message</p>
                  ) : (
                    <div className="space-y-3 max-h-60 overflow-y-auto">
                      {selectedContact.messages.map((msg) => (
                        <div
                          key={msg.id}
                          className="bg-slate-800 p-3 rounded-lg border-l-2 border-blue-500"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2 text-xs text-slate-400">
                              <Clock className="h-3 w-3" />
                              {new Date(msg.sent_at).toLocaleDateString("fr-FR", {
                                day: "numeric",
                                month: "long",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit"
                              })}
                            </div>
                            {msg.is_late && (
                              <Badge variant="outline" className="text-yellow-400 border-yellow-400 text-xs">
                                +{msg.days_late} jour(s)
                              </Badge>
                            )}
                          </div>
                          <p className="text-slate-300 text-sm">{msg.message_text}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Visites de profil */}
                {selectedContact.profile_visits.length > 0 && (
                  <div>
                    <h3 className="text-white font-semibold mb-3">Visites de profil</h3>
                    <div className="space-y-2">
                      {selectedContact.profile_visits.slice(0, 5).map((visit) => (
                        <div
                          key={visit.id}
                          className="flex items-center justify-between text-sm bg-slate-800 p-2 rounded"
                        >
                          <span className="text-slate-300">
                            {new Date(visit.visited_at).toLocaleDateString("fr-FR")}
                          </span>
                          <Badge variant={visit.success ? "default" : "destructive"} className="text-xs">
                            {visit.success ? "Succès" : "Échec"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
