"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import {
  Search,
  UserX,
  Plus,
  Trash2,
  Edit2,
  Calendar,
  Link as LinkIcon,
  AlertCircle,
  CheckCircle,
  Loader2,
  X,
  RefreshCw
} from "lucide-react"
import { useState, useEffect, useCallback } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface BlacklistEntry {
  id: number
  contact_name: string
  linkedin_url: string | null
  reason: string | null
  added_at: string
  added_by: string
  is_active: boolean
}

export default function BlacklistPage() {
  const [searchTerm, setSearchTerm] = useState("")
  const [entries, setEntries] = useState<BlacklistEntry[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState<string | null>(null)

  // Dialog states
  const [addDialogOpen, setAddDialogOpen] = useState(false)
  const [editDialogOpen, setEditDialogOpen] = useState(false)
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false)
  const [selectedEntry, setSelectedEntry] = useState<BlacklistEntry | null>(null)

  // Form states
  const [formData, setFormData] = useState({
    contact_name: "",
    linkedin_url: "",
    reason: ""
  })
  const [submitting, setSubmitting] = useState(false)

  // Fetch blacklist entries
  const fetchBlacklist = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const response = await fetch("/api/blacklist")
      if (!response.ok) {
        throw new Error("Erreur lors du chargement de la blacklist")
      }
      const data = await response.json()
      setEntries(data.entries || [])
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchBlacklist()
  }, [fetchBlacklist])

  // Filter entries by search term
  const filteredEntries = entries.filter(entry =>
    entry.contact_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (entry.reason && entry.reason.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (entry.linkedin_url && entry.linkedin_url.toLowerCase().includes(searchTerm.toLowerCase()))
  )

  // Add entry
  const handleAdd = async () => {
    if (!formData.contact_name.trim()) {
      setError("Le nom du contact est requis")
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      const response = await fetch("/api/blacklist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact_name: formData.contact_name.trim(),
          linkedin_url: formData.linkedin_url.trim() || null,
          reason: formData.reason.trim() || null
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || "Erreur lors de l'ajout")
      }

      setSuccess("Contact ajouté à la blacklist")
      setAddDialogOpen(false)
      setFormData({ contact_name: "", linkedin_url: "", reason: "" })
      fetchBlacklist()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue")
    } finally {
      setSubmitting(false)
    }
  }

  // Edit entry
  const handleEdit = async () => {
    if (!selectedEntry) return
    if (!formData.contact_name.trim()) {
      setError("Le nom du contact est requis")
      return
    }

    try {
      setSubmitting(true)
      setError(null)
      const response = await fetch(`/api/blacklist/${selectedEntry.id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contact_name: formData.contact_name.trim(),
          linkedin_url: formData.linkedin_url.trim() || null,
          reason: formData.reason.trim() || null
        })
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || "Erreur lors de la modification")
      }

      setSuccess("Contact mis à jour")
      setEditDialogOpen(false)
      setSelectedEntry(null)
      setFormData({ contact_name: "", linkedin_url: "", reason: "" })
      fetchBlacklist()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue")
    } finally {
      setSubmitting(false)
    }
  }

  // Delete entry
  const handleDelete = async () => {
    if (!selectedEntry) return

    try {
      setSubmitting(true)
      setError(null)
      const response = await fetch(`/api/blacklist/${selectedEntry.id}`, {
        method: "DELETE"
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || "Erreur lors de la suppression")
      }

      setSuccess("Contact retiré de la blacklist")
      setDeleteDialogOpen(false)
      setSelectedEntry(null)
      fetchBlacklist()
      setTimeout(() => setSuccess(null), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue")
    } finally {
      setSubmitting(false)
    }
  }

  // Open edit dialog
  const openEditDialog = (entry: BlacklistEntry) => {
    setSelectedEntry(entry)
    setFormData({
      contact_name: entry.contact_name,
      linkedin_url: entry.linkedin_url || "",
      reason: entry.reason || ""
    })
    setEditDialogOpen(true)
  }

  // Open delete dialog
  const openDeleteDialog = (entry: BlacklistEntry) => {
    setSelectedEntry(entry)
    setDeleteDialogOpen(true)
  }

  // Format date
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr)
      return date.toLocaleDateString("fr-FR", {
        day: "numeric",
        month: "short",
        year: "numeric"
      })
    } catch {
      return dateStr
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight flex items-center gap-3">
            <UserX className="h-8 w-8 text-red-400" />
            Blacklist
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Contacts exclus des envois automatiques de messages
          </p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <Button
            variant="outline"
            className="gap-2 border-slate-700 hover:bg-slate-800"
            onClick={fetchBlacklist}
            disabled={loading}
          >
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
            Actualiser
          </Button>
          <Button
            className="gap-2 bg-red-600 hover:bg-red-700 text-white"
            onClick={() => {
              setFormData({ contact_name: "", linkedin_url: "", reason: "" })
              setAddDialogOpen(true)
            }}
          >
            <Plus className="h-4 w-4" />
            Ajouter
          </Button>
        </div>
      </div>

      {/* Success / Error Messages */}
      {success && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <CheckCircle className="h-5 w-5" />
          {success}
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 p-4 rounded-lg bg-red-500/10 border border-red-500/20 text-red-400">
          <AlertCircle className="h-5 w-5" />
          {error}
          <Button
            variant="ghost"
            size="sm"
            className="ml-auto"
            onClick={() => setError(null)}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Main Content */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="p-4 border-b border-slate-800">
          <div className="flex items-center justify-between">
            <div className="relative flex-1 max-w-md">
              <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
              <Input
                placeholder="Rechercher par nom, raison ou URL..."
                className="pl-9 bg-slate-950 border-slate-800 focus:border-red-500 text-slate-200"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
            <span className="text-sm text-slate-500">
              {filteredEntries.length} contact{filteredEntries.length > 1 ? 's' : ''} bloqué{filteredEntries.length > 1 ? 's' : ''}
            </span>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
          ) : filteredEntries.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-slate-500">
              <UserX className="h-12 w-12 mb-4 opacity-50" />
              <p className="text-lg font-medium">Aucun contact dans la blacklist</p>
              <p className="text-sm mt-1">
                {searchTerm ? "Essayez une autre recherche" : "Ajoutez des contacts à exclure des envois automatiques"}
              </p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 uppercase bg-slate-950/50 border-b border-slate-800">
                  <tr>
                    <th className="px-6 py-3 font-medium">Nom du contact</th>
                    <th className="px-6 py-3 font-medium">URL LinkedIn</th>
                    <th className="px-6 py-3 font-medium">Raison</th>
                    <th className="px-6 py-3 font-medium">Ajouté le</th>
                    <th className="px-6 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800">
                  {filteredEntries.map((entry) => (
                    <tr key={entry.id} className="hover:bg-slate-800/50 transition-colors group">
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-3">
                          <div className="h-8 w-8 rounded-full bg-red-500/10 flex items-center justify-center text-red-400 border border-red-500/20">
                            <UserX className="h-4 w-4" />
                          </div>
                          <span className="font-medium text-slate-200">
                            {entry.contact_name}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        {entry.linkedin_url ? (
                          <a
                            href={entry.linkedin_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 text-blue-400 hover:text-blue-300 text-xs truncate max-w-[200px]"
                          >
                            <LinkIcon className="h-3 w-3" />
                            {entry.linkedin_url.replace('https://www.linkedin.com/in/', '')}
                          </a>
                        ) : (
                          <span className="text-slate-600 text-xs">Non renseigné</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-slate-400 text-xs">
                          {entry.reason || <span className="text-slate-600 italic">Aucune raison</span>}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center gap-1 text-slate-500 text-xs">
                          <Calendar className="h-3 w-3" />
                          {formatDate(entry.added_at)}
                        </div>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-slate-500 hover:text-blue-400 hover:bg-blue-500/10"
                            onClick={() => openEditDialog(entry)}
                          >
                            <Edit2 className="h-4 w-4" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                            onClick={() => openDeleteDialog(entry)}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Info Card */}
      <Card className="bg-slate-900/50 border-slate-800">
        <CardContent className="p-4">
          <div className="flex items-start gap-3">
            <AlertCircle className="h-5 w-5 text-amber-400 mt-0.5" />
            <div>
              <p className="text-sm text-slate-300 font-medium">Comment fonctionne la blacklist ?</p>
              <p className="text-xs text-slate-500 mt-1">
                Les contacts dans cette liste seront automatiquement ignorés lors de l'envoi de messages d'anniversaire.
                Utilisez cette fonctionnalité pour exclure des concurrents, d'anciens collègues ou toute personne
                que vous ne souhaitez pas contacter automatiquement.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Add Dialog */}
      <Dialog open={addDialogOpen} onOpenChange={setAddDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-slate-200">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <UserX className="h-5 w-5 text-red-400" />
              Ajouter à la blacklist
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              Ce contact sera exclu de tous les envois automatiques de messages.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="add-name">Nom du contact *</Label>
              <Input
                id="add-name"
                placeholder="Ex: Jean Dupont"
                className="bg-slate-950 border-slate-800"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-url">URL LinkedIn (optionnel)</Label>
              <Input
                id="add-url"
                placeholder="https://www.linkedin.com/in/..."
                className="bg-slate-950 border-slate-800"
                value={formData.linkedin_url}
                onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="add-reason">Raison (optionnel)</Label>
              <Textarea
                id="add-reason"
                placeholder="Ex: Concurrent direct, ancien employeur..."
                className="bg-slate-950 border-slate-800 resize-none"
                rows={2}
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setAddDialogOpen(false)}
              className="border-slate-700"
            >
              Annuler
            </Button>
            <Button
              onClick={handleAdd}
              disabled={submitting || !formData.contact_name.trim()}
              className="bg-red-600 hover:bg-red-700"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Ajout...
                </>
              ) : (
                "Ajouter à la blacklist"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={editDialogOpen} onOpenChange={setEditDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-slate-200">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Edit2 className="h-5 w-5 text-blue-400" />
              Modifier l'entrée
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              Modifiez les informations de ce contact dans la blacklist.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Nom du contact *</Label>
              <Input
                id="edit-name"
                className="bg-slate-950 border-slate-800"
                value={formData.contact_name}
                onChange={(e) => setFormData({ ...formData, contact_name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-url">URL LinkedIn</Label>
              <Input
                id="edit-url"
                className="bg-slate-950 border-slate-800"
                value={formData.linkedin_url}
                onChange={(e) => setFormData({ ...formData, linkedin_url: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-reason">Raison</Label>
              <Textarea
                id="edit-reason"
                className="bg-slate-950 border-slate-800 resize-none"
                rows={2}
                value={formData.reason}
                onChange={(e) => setFormData({ ...formData, reason: e.target.value })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditDialogOpen(false)}
              className="border-slate-700"
            >
              Annuler
            </Button>
            <Button
              onClick={handleEdit}
              disabled={submitting || !formData.contact_name.trim()}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Sauvegarde...
                </>
              ) : (
                "Enregistrer"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <DialogContent className="bg-slate-900 border-slate-800 text-slate-200">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-red-400">
              <Trash2 className="h-5 w-5" />
              Confirmer la suppression
            </DialogTitle>
            <DialogDescription className="text-slate-400">
              Êtes-vous sûr de vouloir retirer <strong className="text-white">{selectedEntry?.contact_name}</strong> de la blacklist ?
              Ce contact pourra à nouveau recevoir des messages automatiques.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="mt-4">
            <Button
              variant="outline"
              onClick={() => setDeleteDialogOpen(false)}
              className="border-slate-700"
            >
              Annuler
            </Button>
            <Button
              onClick={handleDelete}
              disabled={submitting}
              className="bg-red-600 hover:bg-red-700"
            >
              {submitting ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Suppression...
                </>
              ) : (
                "Supprimer"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
