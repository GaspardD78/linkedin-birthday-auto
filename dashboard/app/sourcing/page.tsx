"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
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
  Download,
  Filter,
  Users,
  Target,
  TrendingUp,
  Briefcase,
  ChevronLeft,
  ChevronRight,
  ExternalLink,
  RefreshCw,
  X
} from "lucide-react"

interface Profile {
  id: number
  profile_url: string
  first_name: string | null
  last_name: string | null
  full_name: string | null
  headline: string | null
  summary: string | null
  current_company: string | null
  education: string | null
  years_experience: number | null
  skills: string[] | null
  certifications: string[] | null
  fit_score: number | null
  scraped_at: string
  campaign_id: number | null
}

interface SourcingStats {
  total_profiles: number
  avg_fit_score: number
  qualified_count: number
  open_to_work_count: number
  top_companies: Array<{ name: string; count: number }>
  score_distribution: Record<string, number>
}

interface SearchFilters {
  keywords: string
  minFitScore: number
  minYears: number | null
  maxYears: number | null
  company: string
  skills: string
  openToWorkOnly: boolean
}

export default function SourcingPage() {
  // États
  const [profiles, setProfiles] = useState<Profile[]>([])
  const [stats, setStats] = useState<SourcingStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Pagination
  const [page, setPage] = useState(1)
  const [perPage, setPerPage] = useState(25)
  const [totalPages, setTotalPages] = useState(1)
  const [total, setTotal] = useState(0)

  // Tri
  const [sortBy, setSortBy] = useState("fit_score")
  const [sortOrder, setSortOrder] = useState("desc")

  // Filtres
  const [filters, setFilters] = useState<SearchFilters>({
    keywords: "",
    minFitScore: 0,
    minYears: null,
    maxYears: null,
    company: "",
    skills: "",
    openToWorkOnly: false
  })
  const [showFilters, setShowFilters] = useState(false)

  // Detail dialog
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null)

  // Chargement des stats
  const loadStats = useCallback(async () => {
    try {
      const res = await fetch("/api/sourcing/stats?days=30")
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
      console.error("Failed to load stats:", err)
    }
  }, [])

  // Chargement des profils
  const loadProfiles = useCallback(async () => {
    setLoading(true)
    setError(null)

    try {
      const params = new URLSearchParams({
        page: page.toString(),
        per_page: perPage.toString(),
        sort_by: sortBy,
        sort_order: sortOrder
      })

      if (filters.keywords) params.append("keywords", filters.keywords)
      if (filters.minFitScore > 0) params.append("min_fit_score", filters.minFitScore.toString())
      if (filters.minYears) params.append("min_years", filters.minYears.toString())
      if (filters.maxYears) params.append("max_years", filters.maxYears.toString())
      if (filters.company) params.append("company", filters.company)
      if (filters.skills) params.append("skills", filters.skills)
      if (filters.openToWorkOnly) params.append("open_to_work", "true")

      const res = await fetch(`/api/sourcing?${params.toString()}`)

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data = await res.json()
      setProfiles(data.profiles || [])
      setTotal(data.total || 0)
      setTotalPages(data.total_pages || 1)

    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de chargement")
      setProfiles([])
    } finally {
      setLoading(false)
    }
  }, [page, perPage, sortBy, sortOrder, filters])

  // Export CSV
  const handleExport = async () => {
    setExporting(true)
    try {
      const exportFilters: Record<string, unknown> = {}
      if (filters.minFitScore > 0) exportFilters.min_fit_score = filters.minFitScore
      if (filters.keywords) exportFilters.keywords = filters.keywords.split(",").map(k => k.trim())
      if (filters.skills) exportFilters.skills_required = filters.skills.split(",").map(s => s.trim())
      if (filters.company) exportFilters.current_company = [filters.company]
      if (filters.openToWorkOnly) exportFilters.open_to_work_only = true

      const res = await fetch("/api/sourcing/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filters: exportFilters,
          columns: ["full_name", "headline", "current_company", "years_experience", "skills", "fit_score", "profile_url", "scraped_at"]
        })
      })

      if (!res.ok) throw new Error("Export failed")

      const blob = await res.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `sourcing_${new Date().toISOString().split("T")[0]}.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      a.remove()

    } catch (err) {
      setError("Erreur lors de l'export CSV")
    } finally {
      setExporting(false)
    }
  }

  // Effet: charger au montage et quand les paramètres changent
  useEffect(() => {
    loadStats()
  }, [loadStats])

  useEffect(() => {
    loadProfiles()
  }, [loadProfiles])

  // Reset page quand les filtres changent
  const applyFilters = () => {
    setPage(1)
    loadProfiles()
  }

  const clearFilters = () => {
    setFilters({
      keywords: "",
      minFitScore: 0,
      minYears: null,
      maxYears: null,
      company: "",
      skills: "",
      openToWorkOnly: false
    })
    setPage(1)
  }

  // Calcul du score badge color
  const getScoreBadge = (score: number | null) => {
    if (score === null) return <Badge variant="outline">N/A</Badge>
    if (score >= 80) return <Badge className="bg-emerald-500">{score.toFixed(0)}</Badge>
    if (score >= 60) return <Badge className="bg-blue-500">{score.toFixed(0)}</Badge>
    if (score >= 40) return <Badge className="bg-yellow-500">{score.toFixed(0)}</Badge>
    return <Badge variant="outline">{score.toFixed(0)}</Badge>
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sourcing Recruteur</h1>
          <p className="text-slate-400">Recherche et export de profils qualifiés</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowFilters(!showFilters)}
            className="gap-2"
          >
            <Filter className="h-4 w-4" />
            Filtres
          </Button>
          <Button
            onClick={handleExport}
            disabled={exporting || profiles.length === 0}
            className="gap-2 bg-emerald-600 hover:bg-emerald-700"
          >
            <Download className="h-4 w-4" />
            {exporting ? "Export..." : "Export CSV"}
          </Button>
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
                  <p className="text-2xl font-bold text-white">{stats.total_profiles}</p>
                  <p className="text-xs text-slate-400">Profils scrapés</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-emerald-500/20 rounded-lg">
                  <Target className="h-5 w-5 text-emerald-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.qualified_count}</p>
                  <p className="text-xs text-slate-400">Qualifiés (score &gt; 70)</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-purple-500/20 rounded-lg">
                  <TrendingUp className="h-5 w-5 text-purple-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.avg_fit_score.toFixed(1)}</p>
                  <p className="text-xs text-slate-400">Score moyen</p>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-slate-900 border-slate-800">
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-cyan-500/20 rounded-lg">
                  <Briefcase className="h-5 w-5 text-cyan-400" />
                </div>
                <div>
                  <p className="text-2xl font-bold text-white">{stats.open_to_work_count}</p>
                  <p className="text-xs text-slate-400">Open to Work</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Filters Panel */}
      {showFilters && (
        <Card className="bg-slate-900 border-slate-800">
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-white">Filtres de recherche</CardTitle>
              <Button variant="ghost" size="sm" onClick={clearFilters}>
                <X className="h-4 w-4 mr-1" /> Effacer
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Keywords */}
              <div className="space-y-2">
                <Label className="text-slate-300">Mots-clés (séparés par virgule)</Label>
                <Input
                  placeholder="Python, DevOps, AWS..."
                  value={filters.keywords}
                  onChange={(e) => setFilters({ ...filters, keywords: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>

              {/* Company */}
              <div className="space-y-2">
                <Label className="text-slate-300">Entreprise</Label>
                <Input
                  placeholder="Google, Microsoft..."
                  value={filters.company}
                  onChange={(e) => setFilters({ ...filters, company: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>

              {/* Skills */}
              <div className="space-y-2">
                <Label className="text-slate-300">Compétences requises</Label>
                <Input
                  placeholder="Kubernetes, Terraform..."
                  value={filters.skills}
                  onChange={(e) => setFilters({ ...filters, skills: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Min Fit Score */}
              <div className="space-y-2">
                <Label className="text-slate-300">Score minimum: {filters.minFitScore}</Label>
                <Slider
                  value={[filters.minFitScore]}
                  onValueChange={([value]) => setFilters({ ...filters, minFitScore: value })}
                  max={100}
                  step={5}
                  className="py-2"
                />
              </div>

              {/* Experience */}
              <div className="space-y-2">
                <Label className="text-slate-300">Années d'expérience</Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={filters.minYears || ""}
                    onChange={(e) => setFilters({ ...filters, minYears: e.target.value ? parseInt(e.target.value) : null })}
                    className="bg-slate-800 border-slate-700 text-white w-20"
                  />
                  <span className="text-slate-400 self-center">-</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={filters.maxYears || ""}
                    onChange={(e) => setFilters({ ...filters, maxYears: e.target.value ? parseInt(e.target.value) : null })}
                    className="bg-slate-800 border-slate-700 text-white w-20"
                  />
                </div>
              </div>

              {/* Open to Work */}
              <div className="space-y-2">
                <Label className="text-slate-300">Disponibilité</Label>
                <div className="flex items-center gap-2 pt-2">
                  <Switch
                    checked={filters.openToWorkOnly}
                    onCheckedChange={(checked) => setFilters({ ...filters, openToWorkOnly: checked })}
                  />
                  <span className="text-sm text-slate-400">Open to Work uniquement</span>
                </div>
              </div>
            </div>

            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={clearFilters}>Réinitialiser</Button>
              <Button onClick={applyFilters} className="bg-blue-600 hover:bg-blue-700">
                <Search className="h-4 w-4 mr-2" />
                Rechercher
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-white">Résultats</CardTitle>
              <CardDescription>{total} profils trouvés</CardDescription>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-2">
                <Label className="text-slate-400 text-sm">Trier par:</Label>
                <Select value={sortBy} onValueChange={setSortBy}>
                  <SelectTrigger className="w-[140px] bg-slate-800 border-slate-700">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="fit_score">Score</SelectItem>
                    <SelectItem value="years_experience">Expérience</SelectItem>
                    <SelectItem value="scraped_at">Date</SelectItem>
                    <SelectItem value="full_name">Nom</SelectItem>
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
              </div>
              <Button variant="ghost" size="icon" onClick={loadProfiles}>
                <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {error ? (
            <div className="text-center py-8 text-red-400">{error}</div>
          ) : loading ? (
            <div className="text-center py-8 text-slate-400">Chargement...</div>
          ) : profiles.length === 0 ? (
            <div className="text-center py-8 text-slate-400">Aucun profil trouvé</div>
          ) : (
            <>
              <Table>
                <TableHeader>
                  <TableRow className="border-slate-800">
                    <TableHead className="text-slate-400">Nom</TableHead>
                    <TableHead className="text-slate-400">Titre</TableHead>
                    <TableHead className="text-slate-400">Entreprise</TableHead>
                    <TableHead className="text-slate-400">Exp.</TableHead>
                    <TableHead className="text-slate-400">Score</TableHead>
                    <TableHead className="text-slate-400">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {profiles.map((profile) => (
                    <TableRow
                      key={profile.id}
                      className="border-slate-800 hover:bg-slate-800/50 cursor-pointer"
                      onClick={() => setSelectedProfile(profile)}
                    >
                      <TableCell className="font-medium text-white">
                        {profile.full_name || "N/A"}
                      </TableCell>
                      <TableCell className="text-slate-300 max-w-[250px] truncate">
                        {profile.headline || "-"}
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {profile.current_company || "-"}
                      </TableCell>
                      <TableCell className="text-slate-300">
                        {profile.years_experience !== null ? `${profile.years_experience} ans` : "-"}
                      </TableCell>
                      <TableCell>
                        {getScoreBadge(profile.fit_score)}
                      </TableCell>
                      <TableCell>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={(e) => {
                            e.stopPropagation()
                            window.open(profile.profile_url, "_blank")
                          }}
                        >
                          <ExternalLink className="h-4 w-4 text-blue-400" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>

              {/* Pagination */}
              <div className="flex items-center justify-between mt-4">
                <div className="text-sm text-slate-400">
                  Page {page} sur {totalPages} ({total} résultats)
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

      {/* Profile Detail Dialog */}
      <Dialog open={!!selectedProfile} onOpenChange={() => setSelectedProfile(null)}>
        <DialogContent className="bg-slate-900 border-slate-800 max-w-2xl max-h-[80vh] overflow-y-auto">
          {selectedProfile && (
            <>
              <DialogHeader>
                <DialogTitle className="text-white text-xl">
                  {selectedProfile.full_name || "Profil"}
                </DialogTitle>
                <DialogDescription className="text-slate-400">
                  {selectedProfile.headline}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                {/* Score & Experience */}
                <div className="flex items-center gap-4">
                  <div className="flex items-center gap-2">
                    <span className="text-slate-400">Score:</span>
                    {getScoreBadge(selectedProfile.fit_score)}
                  </div>
                  {selectedProfile.years_experience !== null && (
                    <div className="flex items-center gap-2">
                      <span className="text-slate-400">Expérience:</span>
                      <Badge variant="outline">{selectedProfile.years_experience} ans</Badge>
                    </div>
                  )}
                </div>

                {/* Company */}
                {selectedProfile.current_company && (
                  <div>
                    <Label className="text-slate-400">Entreprise actuelle</Label>
                    <p className="text-white">{selectedProfile.current_company}</p>
                  </div>
                )}

                {/* Summary */}
                {selectedProfile.summary && (
                  <div>
                    <Label className="text-slate-400">À propos</Label>
                    <p className="text-slate-300 text-sm">{selectedProfile.summary}</p>
                  </div>
                )}

                {/* Skills */}
                {selectedProfile.skills && selectedProfile.skills.length > 0 && (
                  <div>
                    <Label className="text-slate-400">Compétences</Label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {selectedProfile.skills.map((skill, i) => (
                        <Badge key={i} variant="secondary" className="bg-slate-800">
                          {skill}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Certifications */}
                {selectedProfile.certifications && selectedProfile.certifications.length > 0 && (
                  <div>
                    <Label className="text-slate-400">Certifications</Label>
                    <div className="flex flex-wrap gap-2 mt-1">
                      {selectedProfile.certifications.map((cert, i) => (
                        <Badge key={i} variant="outline" className="border-emerald-500 text-emerald-400">
                          {cert}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Scraped date */}
                <div className="text-xs text-slate-500 pt-2 border-t border-slate-800">
                  Scrapé le {new Date(selectedProfile.scraped_at).toLocaleDateString("fr-FR", {
                    day: "numeric",
                    month: "long",
                    year: "numeric"
                  })}
                </div>

                {/* Actions */}
                <div className="flex gap-2 pt-2">
                  <Button
                    className="flex-1 bg-blue-600 hover:bg-blue-700"
                    onClick={() => window.open(selectedProfile.profile_url, "_blank")}
                  >
                    <ExternalLink className="h-4 w-4 mr-2" />
                    Voir sur LinkedIn
                  </Button>
                </div>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}
