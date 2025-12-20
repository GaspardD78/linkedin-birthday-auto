"use client"

import { useState, useEffect, useCallback } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Slider } from "@/components/ui/slider"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
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
  DialogFooter,
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
  X,
  Plus,
  Play,
  Pause,
  Trash2,
  MapPin,
  GraduationCap,
  Languages,
  Award,
  Clock,
  CheckCircle,
  AlertCircle,
  Loader2
} from "lucide-react"

// ═══════════════════════════════════════════════════════════════
// INTERFACES
// ═══════════════════════════════════════════════════════════════

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
  // Champs enrichis
  location: string | null
  languages: string[] | null
  work_history: Array<{ title?: string; company?: string; duration_text?: string }> | null
  connection_degree: string | null
  school: string | null
  degree: string | null
  job_title: string | null
  seniority_level: string | null
  endorsements_count: number | null
  profile_picture_url: string | null
  open_to_work: boolean | null
}

interface Campaign {
  id: number
  name: string
  status: string
  job_title: string
  keywords: string[]
  location: string
  profiles_target: number
  profiles_found: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  filters: Record<string, unknown>
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
  campaignId: number | null
}

interface JobDescriptionForm {
  title: string
  description: string
  keywords: string
  location: string
  titleFilters: string
  keywordsExclude: string
  seniorityLevel: string[]
  languages: string
  yearsExpMin: number | null
  yearsExpMax: number | null
  profilesTarget: number
}

// ═══════════════════════════════════════════════════════════════
// COMPONENT
// ═══════════════════════════════════════════════════════════════

export default function SourcingPage() {
  // Tab state
  const [activeTab, setActiveTab] = useState("campaigns")

  // Campaigns
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loadingCampaigns, setLoadingCampaigns] = useState(true)
  const [selectedCampaign, setSelectedCampaign] = useState<Campaign | null>(null)

  // Create Campaign Dialog
  const [showCreateDialog, setShowCreateDialog] = useState(false)
  const [creating, setCreating] = useState(false)
  const [jobForm, setJobForm] = useState<JobDescriptionForm>({
    title: "",
    description: "",
    keywords: "",
    location: "France",
    titleFilters: "",
    keywordsExclude: "",
    seniorityLevel: [],
    languages: "",
    yearsExpMin: null,
    yearsExpMax: null,
    profilesTarget: 50
  })

  // Profiles
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

  // Sorting
  const [sortBy, setSortBy] = useState("fit_score")
  const [sortOrder, setSortOrder] = useState("desc")

  // Filters
  const [filters, setFilters] = useState<SearchFilters>({
    keywords: "",
    minFitScore: 0,
    minYears: null,
    maxYears: null,
    company: "",
    skills: "",
    openToWorkOnly: false,
    campaignId: null
  })
  const [showFilters, setShowFilters] = useState(false)

  // Profile Detail Dialog
  const [selectedProfile, setSelectedProfile] = useState<Profile | null>(null)

  // ═══════════════════════════════════════════════════════════════
  // DATA LOADING
  // ═══════════════════════════════════════════════════════════════

  // Load campaigns
  const loadCampaigns = useCallback(async () => {
    setLoadingCampaigns(true)
    try {
      const res = await fetch("/api/sourcing/campaigns")
      if (res.ok) {
        const data = await res.json()
        setCampaigns(data || [])
      }
    } catch (err) {
    } finally {
      setLoadingCampaigns(false)
    }
  }, [])

  // Load stats
  const loadStats = useCallback(async () => {
    try {
      const params = new URLSearchParams({ days: "30" })
      if (filters.campaignId) params.append("campaign_id", filters.campaignId.toString())

      const res = await fetch(`/api/sourcing/stats?${params.toString()}`)
      if (res.ok) {
        const data = await res.json()
        setStats(data)
      }
    } catch (err) {
    }
  }, [filters.campaignId])

  // Load profiles
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
      if (filters.campaignId) params.append("campaign_id", filters.campaignId.toString())

      const res = await fetch(`/api/sourcing?${params.toString()}`)

      if (!res.ok) throw new Error(`HTTP ${res.status}`)

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

  // ═══════════════════════════════════════════════════════════════
  // CAMPAIGN ACTIONS
  // ═══════════════════════════════════════════════════════════════

  const createCampaign = async (autoStart: boolean = false) => {
    setCreating(true)
    try {
      const keywords = jobForm.keywords.split(",").map(k => k.trim()).filter(k => k)

      const payload = {
        name: `${jobForm.title} - ${new Date().toLocaleDateString("fr-FR")}`,
        job_description: {
          title: jobForm.title,
          description: jobForm.description,
          keywords,
          location: jobForm.location,
          title_filters: jobForm.titleFilters ? jobForm.titleFilters.split(",").map(t => t.trim()) : null,
          keywords_exclude: jobForm.keywordsExclude ? jobForm.keywordsExclude.split(",").map(k => k.trim()) : null,
          seniority_level: jobForm.seniorityLevel.length > 0 ? jobForm.seniorityLevel : null,
          languages: jobForm.languages ? jobForm.languages.split(",").map(l => l.trim()) : null,
          years_experience_min: jobForm.yearsExpMin,
          years_experience_max: jobForm.yearsExpMax,
          profiles_target: jobForm.profilesTarget
        },
        auto_start: autoStart
      }

      const res = await fetch("/api/sourcing/campaigns", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      })

      if (!res.ok) throw new Error("Failed to create campaign")

      setShowCreateDialog(false)
      setJobForm({
        title: "",
        description: "",
        keywords: "",
        location: "France",
        titleFilters: "",
        keywordsExclude: "",
        seniorityLevel: [],
        languages: "",
        yearsExpMin: null,
        yearsExpMax: null,
        profilesTarget: 50
      })
      loadCampaigns()

    } catch (err) {
      setError("Erreur lors de la création de la campagne")
    } finally {
      setCreating(false)
    }
  }

  const startCampaign = async (campaignId: number) => {
    try {
      const res = await fetch(`/api/sourcing/campaigns/${campaignId}/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ dry_run: false })
      })
      if (res.ok) loadCampaigns()
    } catch (err) {
      setError("Erreur lors du démarrage")
    }
  }

  const stopCampaign = async (campaignId: number) => {
    try {
      const res = await fetch(`/api/sourcing/campaigns/${campaignId}/stop`, {
        method: "POST"
      })
      if (res.ok) loadCampaigns()
    } catch (err) {
      setError("Erreur lors de l'arrêt")
    }
  }

  const deleteCampaign = async (campaignId: number) => {
    if (!confirm("Supprimer cette campagne ?")) return
    try {
      const res = await fetch(`/api/sourcing/campaigns/${campaignId}`, {
        method: "DELETE"
      })
      if (res.ok) loadCampaigns()
    } catch (err) {
      setError("Erreur lors de la suppression")
    }
  }

  // ═══════════════════════════════════════════════════════════════
  // EXPORT
  // ═══════════════════════════════════════════════════════════════

  const handleExport = async () => {
    setExporting(true)
    try {
      const exportFilters: Record<string, unknown> = {}
      if (filters.minFitScore > 0) exportFilters.min_fit_score = filters.minFitScore
      if (filters.keywords) exportFilters.keywords = filters.keywords.split(",").map(k => k.trim())
      if (filters.skills) exportFilters.skills_required = filters.skills.split(",").map(s => s.trim())
      if (filters.company) exportFilters.current_company = [filters.company]
      if (filters.openToWorkOnly) exportFilters.open_to_work_only = true
      if (filters.campaignId) exportFilters.campaign_id = filters.campaignId

      const res = await fetch("/api/sourcing/export", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filters: exportFilters,
          columns: [
            "full_name", "headline", "job_title", "current_company", "location",
            "years_experience", "seniority_level", "skills", "languages",
            "fit_score", "open_to_work", "profile_url", "scraped_at"
          ]
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

  // ═══════════════════════════════════════════════════════════════
  // EFFECTS
  // ═══════════════════════════════════════════════════════════════

  useEffect(() => {
    loadCampaigns()
    loadStats()
  }, [loadCampaigns, loadStats])

  useEffect(() => {
    if (activeTab === "profiles") {
      loadProfiles()
    }
  }, [activeTab, loadProfiles])

  // ═══════════════════════════════════════════════════════════════
  // HELPERS
  // ═══════════════════════════════════════════════════════════════

  const getScoreBadge = (score: number | null) => {
    if (score === null) return <Badge variant="outline">N/A</Badge>
    if (score >= 80) return <Badge className="bg-emerald-500">{score.toFixed(0)}</Badge>
    if (score >= 60) return <Badge className="bg-blue-500">{score.toFixed(0)}</Badge>
    if (score >= 40) return <Badge className="bg-yellow-500">{score.toFixed(0)}</Badge>
    return <Badge variant="outline">{score.toFixed(0)}</Badge>
  }

  const getCampaignStatusBadge = (status: string) => {
    switch (status) {
      case "running": return <Badge className="bg-blue-500"><Loader2 className="h-3 w-3 mr-1 animate-spin" />En cours</Badge>
      case "completed": return <Badge className="bg-emerald-500"><CheckCircle className="h-3 w-3 mr-1" />Terminé</Badge>
      case "failed": return <Badge className="bg-red-500"><AlertCircle className="h-3 w-3 mr-1" />Échec</Badge>
      default: return <Badge variant="outline"><Clock className="h-3 w-3 mr-1" />En attente</Badge>
    }
  }

  const clearFilters = () => {
    setFilters({
      keywords: "",
      minFitScore: 0,
      minYears: null,
      maxYears: null,
      company: "",
      skills: "",
      openToWorkOnly: false,
      campaignId: null
    })
    setPage(1)
  }

  const selectCampaignForProfiles = (campaign: Campaign) => {
    setFilters({ ...filters, campaignId: campaign.id })
    setActiveTab("profiles")
  }

  // ═══════════════════════════════════════════════════════════════
  // RENDER
  // ═══════════════════════════════════════════════════════════════

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Sourcing Recruteur</h1>
          <p className="text-slate-400">Campagnes de recherche et profils candidats</p>
        </div>
        <Button onClick={() => setShowCreateDialog(true)} className="gap-2 bg-emerald-600 hover:bg-emerald-700">
          <Plus className="h-4 w-4" />
          Nouvelle Campagne
        </Button>
      </div>

      {error && (
        <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4 text-red-400">
          {error}
          <Button variant="ghost" size="sm" className="ml-2" onClick={() => setError(null)}>
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-slate-800">
          <TabsTrigger value="campaigns" className="data-[state=active]:bg-slate-700">
            <Briefcase className="h-4 w-4 mr-2" />
            Campagnes
          </TabsTrigger>
          <TabsTrigger value="profiles" className="data-[state=active]:bg-slate-700">
            <Users className="h-4 w-4 mr-2" />
            Profils ({total})
          </TabsTrigger>
        </TabsList>

        {/* ═══════════════════════════════════════════════════════════════
            TAB: CAMPAGNES
        ═══════════════════════════════════════════════════════════════ */}
        <TabsContent value="campaigns" className="space-y-4">
          {/* Stats */}
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

          {/* Campaigns List */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">Mes Campagnes</CardTitle>
                <Button variant="ghost" size="icon" onClick={loadCampaigns}>
                  <RefreshCw className={`h-4 w-4 ${loadingCampaigns ? "animate-spin" : ""}`} />
                </Button>
              </div>
            </CardHeader>
            <CardContent>
              {loadingCampaigns ? (
                <div className="text-center py-8 text-slate-400">Chargement...</div>
              ) : campaigns.length === 0 ? (
                <div className="text-center py-8">
                  <p className="text-slate-400 mb-4">Aucune campagne créée</p>
                  <Button onClick={() => setShowCreateDialog(true)} className="gap-2">
                    <Plus className="h-4 w-4" />
                    Créer ma première campagne
                  </Button>
                </div>
              ) : (
                <div className="space-y-3">
                  {campaigns.map((campaign) => (
                    <div
                      key={campaign.id}
                      className="flex items-center justify-between p-4 bg-slate-800 rounded-lg hover:bg-slate-800/80"
                    >
                      <div className="flex-1">
                        <div className="flex items-center gap-3">
                          <h3 className="text-white font-medium">{campaign.name}</h3>
                          {getCampaignStatusBadge(campaign.status)}
                        </div>
                        <div className="flex items-center gap-4 mt-1 text-sm text-slate-400">
                          <span>{campaign.job_title}</span>
                          <span>•</span>
                          <span><MapPin className="h-3 w-3 inline mr-1" />{campaign.location}</span>
                          <span>•</span>
                          <span>{campaign.profiles_found}/{campaign.profiles_target} profils</span>
                        </div>
                        <div className="flex flex-wrap gap-1 mt-2">
                          {campaign.keywords.slice(0, 5).map((kw, i) => (
                            <Badge key={i} variant="secondary" className="bg-slate-700 text-xs">
                              {kw}
                            </Badge>
                          ))}
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {campaign.status === "pending" && (
                          <Button size="sm" onClick={() => startCampaign(campaign.id)} className="bg-blue-600 hover:bg-blue-700">
                            <Play className="h-4 w-4 mr-1" />
                            Lancer
                          </Button>
                        )}
                        {campaign.status === "running" && (
                          <Button size="sm" variant="outline" onClick={() => stopCampaign(campaign.id)}>
                            <Pause className="h-4 w-4 mr-1" />
                            Arrêter
                          </Button>
                        )}
                        {(campaign.status === "completed" || campaign.profiles_found > 0) && (
                          <Button size="sm" variant="outline" onClick={() => selectCampaignForProfiles(campaign)}>
                            <Users className="h-4 w-4 mr-1" />
                            Voir profils
                          </Button>
                        )}
                        <Button size="sm" variant="ghost" onClick={() => deleteCampaign(campaign.id)}>
                          <Trash2 className="h-4 w-4 text-red-400" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ═══════════════════════════════════════════════════════════════
            TAB: PROFILS
        ═══════════════════════════════════════════════════════════════ */}
        <TabsContent value="profiles" className="space-y-4">
          {/* Filters */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-white">Filtres de recherche</CardTitle>
                <div className="flex gap-2">
                  <Button variant="ghost" size="sm" onClick={clearFilters}>
                    <X className="h-4 w-4 mr-1" /> Effacer
                  </Button>
                  <Button variant="outline" onClick={handleExport} disabled={exporting || profiles.length === 0}>
                    <Download className="h-4 w-4 mr-1" />
                    {exporting ? "Export..." : "Export CSV"}
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {/* Campaign Filter */}
                <div className="space-y-2">
                  <Label className="text-slate-300">Campagne</Label>
                  <Select
                    value={filters.campaignId?.toString() || "all"}
                    onValueChange={(v) => setFilters({ ...filters, campaignId: v === "all" ? null : parseInt(v) })}
                  >
                    <SelectTrigger className="bg-slate-800 border-slate-700">
                      <SelectValue placeholder="Toutes" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="all">Toutes les campagnes</SelectItem>
                      {campaigns.map((c) => (
                        <SelectItem key={c.id} value={c.id.toString()}>{c.name}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                {/* Keywords */}
                <div className="space-y-2">
                  <Label className="text-slate-300">Mots-clés</Label>
                  <Input
                    placeholder="Python, DevOps..."
                    value={filters.keywords}
                    onChange={(e) => setFilters({ ...filters, keywords: e.target.value })}
                    className="bg-slate-800 border-slate-700 text-white"
                  />
                </div>

                {/* Min Fit Score */}
                <div className="space-y-2">
                  <Label className="text-slate-300">Score min: {filters.minFitScore}</Label>
                  <Slider
                    value={[filters.minFitScore]}
                    onValueChange={([value]) => setFilters({ ...filters, minFitScore: value })}
                    max={100}
                    step={5}
                  />
                </div>

                {/* Open to Work */}
                <div className="space-y-2">
                  <Label className="text-slate-300">Disponibilité</Label>
                  <div className="flex items-center gap-2 pt-2">
                    <Switch
                      checked={filters.openToWorkOnly}
                      onCheckedChange={(checked) => setFilters({ ...filters, openToWorkOnly: checked })}
                    />
                    <span className="text-sm text-slate-400">Open to Work</span>
                  </div>
                </div>
              </div>

              <div className="flex justify-end">
                <Button onClick={() => { setPage(1); loadProfiles(); }} className="bg-blue-600 hover:bg-blue-700">
                  <Search className="h-4 w-4 mr-2" />
                  Rechercher
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle className="text-white">Résultats</CardTitle>
                  <CardDescription>{total} profils trouvés</CardDescription>
                </div>
                <div className="flex items-center gap-4">
                  <Select value={sortBy} onValueChange={setSortBy}>
                    <SelectTrigger className="w-[140px] bg-slate-800 border-slate-700">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="fit_score">Score</SelectItem>
                      <SelectItem value="years_experience">Expérience</SelectItem>
                      <SelectItem value="scraped_at">Date</SelectItem>
                    </SelectContent>
                  </Select>
                  <Button variant="ghost" size="icon" onClick={loadProfiles}>
                    <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loading ? (
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
                        <TableHead className="text-slate-400">Lieu</TableHead>
                        <TableHead className="text-slate-400">Exp.</TableHead>
                        <TableHead className="text-slate-400">Score</TableHead>
                        <TableHead className="text-slate-400">OTW</TableHead>
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
                          <TableCell className="text-slate-300 max-w-[200px] truncate">
                            {profile.job_title || profile.headline || "-"}
                          </TableCell>
                          <TableCell className="text-slate-300">
                            {profile.current_company || "-"}
                          </TableCell>
                          <TableCell className="text-slate-300 text-sm">
                            {profile.location || "-"}
                          </TableCell>
                          <TableCell className="text-slate-300">
                            {profile.years_experience !== null ? `${profile.years_experience}a` : "-"}
                          </TableCell>
                          <TableCell>
                            {getScoreBadge(profile.fit_score)}
                          </TableCell>
                          <TableCell>
                            {profile.open_to_work && (
                              <Badge className="bg-emerald-500/20 text-emerald-400 text-xs">OTW</Badge>
                            )}
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>

                  {/* Pagination */}
                  <div className="flex items-center justify-between mt-4">
                    <div className="text-sm text-slate-400">
                      Page {page}/{totalPages}
                    </div>
                    <div className="flex items-center gap-2">
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
        </TabsContent>
      </Tabs>

      {/* ═══════════════════════════════════════════════════════════════
          CREATE CAMPAIGN DIALOG
      ═══════════════════════════════════════════════════════════════ */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="bg-slate-900 border-slate-800 max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="text-white text-xl">Nouvelle Campagne de Sourcing</DialogTitle>
            <DialogDescription>
              Définissez votre fiche de poste pour lancer une recherche automatisée
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-6 py-4">
            {/* Job Title */}
            <div className="space-y-2">
              <Label className="text-slate-300">Titre du poste *</Label>
              <Input
                placeholder="ex: DevOps Engineer, Data Scientist..."
                value={jobForm.title}
                onChange={(e) => setJobForm({ ...jobForm, title: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>

            {/* Description */}
            <div className="space-y-2">
              <Label className="text-slate-300">Description (optionnel)</Label>
              <Textarea
                placeholder="Description du poste..."
                value={jobForm.description}
                onChange={(e) => setJobForm({ ...jobForm, description: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white h-20"
              />
            </div>

            {/* Keywords */}
            <div className="space-y-2">
              <Label className="text-slate-300">
                Mots-clés de recherche * (séparés par virgule)
              </Label>
              <Input
                placeholder="ex: DevOps, AWS|Azure, Kubernetes, -junior"
                value={jobForm.keywords}
                onChange={(e) => setJobForm({ ...jobForm, keywords: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white"
              />
              <p className="text-xs text-slate-500">
                Utilisez | pour OR (AWS|Azure), - pour exclure (-junior), " " pour phrases exactes
              </p>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Location */}
              <div className="space-y-2">
                <Label className="text-slate-300">Localisation</Label>
                <Input
                  placeholder="France, Paris..."
                  value={jobForm.location}
                  onChange={(e) => setJobForm({ ...jobForm, location: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>

              {/* Profiles Target */}
              <div className="space-y-2">
                <Label className="text-slate-300">Nombre de profils cibles</Label>
                <Input
                  type="number"
                  min={1}
                  max={500}
                  value={jobForm.profilesTarget}
                  onChange={(e) => setJobForm({ ...jobForm, profilesTarget: parseInt(e.target.value) || 50 })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
            </div>

            {/* Seniority Level */}
            <div className="space-y-2">
              <Label className="text-slate-300">Niveau de séniorité</Label>
              <div className="flex flex-wrap gap-2">
                {["Entry", "Associate", "Mid-Senior", "Director", "VP", "CXO"].map((level) => (
                  <Badge
                    key={level}
                    variant={jobForm.seniorityLevel.includes(level) ? "default" : "outline"}
                    className={`cursor-pointer ${jobForm.seniorityLevel.includes(level) ? "bg-blue-600" : ""}`}
                    onClick={() => {
                      const newLevels = jobForm.seniorityLevel.includes(level)
                        ? jobForm.seniorityLevel.filter(l => l !== level)
                        : [...jobForm.seniorityLevel, level]
                      setJobForm({ ...jobForm, seniorityLevel: newLevels })
                    }}
                  >
                    {level}
                  </Badge>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              {/* Years Experience */}
              <div className="space-y-2">
                <Label className="text-slate-300">Années d'expérience</Label>
                <div className="flex gap-2">
                  <Input
                    type="number"
                    placeholder="Min"
                    value={jobForm.yearsExpMin || ""}
                    onChange={(e) => setJobForm({ ...jobForm, yearsExpMin: e.target.value ? parseInt(e.target.value) : null })}
                    className="bg-slate-800 border-slate-700 text-white w-20"
                  />
                  <span className="text-slate-400 self-center">-</span>
                  <Input
                    type="number"
                    placeholder="Max"
                    value={jobForm.yearsExpMax || ""}
                    onChange={(e) => setJobForm({ ...jobForm, yearsExpMax: e.target.value ? parseInt(e.target.value) : null })}
                    className="bg-slate-800 border-slate-700 text-white w-20"
                  />
                </div>
              </div>

              {/* Languages */}
              <div className="space-y-2">
                <Label className="text-slate-300">Langues requises</Label>
                <Input
                  placeholder="Français, Anglais..."
                  value={jobForm.languages}
                  onChange={(e) => setJobForm({ ...jobForm, languages: e.target.value })}
                  className="bg-slate-800 border-slate-700 text-white"
                />
              </div>
            </div>

            {/* Keywords Exclude */}
            <div className="space-y-2">
              <Label className="text-slate-300">Mots-clés à exclure</Label>
              <Input
                placeholder="ex: stagiaire, intern, freelance..."
                value={jobForm.keywordsExclude}
                onChange={(e) => setJobForm({ ...jobForm, keywordsExclude: e.target.value })}
                className="bg-slate-800 border-slate-700 text-white"
              />
            </div>
          </div>

          <DialogFooter className="gap-2">
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Annuler
            </Button>
            <Button
              onClick={() => createCampaign(false)}
              disabled={creating || !jobForm.title || !jobForm.keywords}
              variant="outline"
            >
              Créer (sans lancer)
            </Button>
            <Button
              onClick={() => createCampaign(true)}
              disabled={creating || !jobForm.title || !jobForm.keywords}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              {creating ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Play className="h-4 w-4 mr-2" />}
              Créer et Lancer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ═══════════════════════════════════════════════════════════════
          PROFILE DETAIL DIALOG
      ═══════════════════════════════════════════════════════════════ */}
      <Dialog open={!!selectedProfile} onOpenChange={() => setSelectedProfile(null)}>
        <DialogContent className="bg-slate-900 border-slate-800 max-w-2xl max-h-[85vh] overflow-y-auto">
          {selectedProfile && (
            <>
              <DialogHeader>
                <div className="flex items-start gap-4">
                  {selectedProfile.profile_picture_url && (
                    <img
                      src={selectedProfile.profile_picture_url}
                      alt=""
                      className="w-16 h-16 rounded-full object-cover"
                    />
                  )}
                  <div className="flex-1">
                    <DialogTitle className="text-white text-xl flex items-center gap-2">
                      {selectedProfile.full_name || "Profil"}
                      {selectedProfile.open_to_work && (
                        <Badge className="bg-emerald-500/20 text-emerald-400">Open to Work</Badge>
                      )}
                    </DialogTitle>
                    <DialogDescription className="text-slate-300">
                      {selectedProfile.job_title || selectedProfile.headline}
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-4 mt-4">
                {/* Badges row */}
                <div className="flex flex-wrap items-center gap-3">
                  {getScoreBadge(selectedProfile.fit_score)}
                  {selectedProfile.years_experience !== null && (
                    <Badge variant="outline">{selectedProfile.years_experience} ans exp.</Badge>
                  )}
                  {selectedProfile.seniority_level && (
                    <Badge variant="secondary">{selectedProfile.seniority_level}</Badge>
                  )}
                  {selectedProfile.connection_degree && (
                    <Badge variant="outline">{selectedProfile.connection_degree}</Badge>
                  )}
                </div>

                {/* Info grid */}
                <div className="grid grid-cols-2 gap-4">
                  {selectedProfile.current_company && (
                    <div>
                      <Label className="text-slate-400 text-xs">Entreprise</Label>
                      <p className="text-white">{selectedProfile.current_company}</p>
                    </div>
                  )}
                  {selectedProfile.location && (
                    <div>
                      <Label className="text-slate-400 text-xs flex items-center gap-1">
                        <MapPin className="h-3 w-3" />Localisation
                      </Label>
                      <p className="text-white">{selectedProfile.location}</p>
                    </div>
                  )}
                  {selectedProfile.school && (
                    <div>
                      <Label className="text-slate-400 text-xs flex items-center gap-1">
                        <GraduationCap className="h-3 w-3" />Formation
                      </Label>
                      <p className="text-white">{selectedProfile.degree || ""} {selectedProfile.school}</p>
                    </div>
                  )}
                  {selectedProfile.languages && selectedProfile.languages.length > 0 && (
                    <div>
                      <Label className="text-slate-400 text-xs flex items-center gap-1">
                        <Languages className="h-3 w-3" />Langues
                      </Label>
                      <p className="text-white">{selectedProfile.languages.join(", ")}</p>
                    </div>
                  )}
                </div>

                {/* Summary */}
                {selectedProfile.summary && (
                  <div>
                    <Label className="text-slate-400 text-xs">À propos</Label>
                    <p className="text-slate-300 text-sm mt-1">{selectedProfile.summary}</p>
                  </div>
                )}

                {/* Work History */}
                {selectedProfile.work_history && selectedProfile.work_history.length > 0 && (
                  <div>
                    <Label className="text-slate-400 text-xs flex items-center gap-1">
                      <Briefcase className="h-3 w-3" />Expériences
                    </Label>
                    <div className="mt-2 space-y-2">
                      {selectedProfile.work_history.slice(0, 5).map((exp, i) => (
                        <div key={i} className="bg-slate-800 p-2 rounded text-sm">
                          <p className="text-white font-medium">{exp.title}</p>
                          <p className="text-slate-400">{exp.company}</p>
                          {exp.duration_text && <p className="text-slate-500 text-xs">{exp.duration_text}</p>}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Skills */}
                {selectedProfile.skills && selectedProfile.skills.length > 0 && (
                  <div>
                    <Label className="text-slate-400 text-xs">Compétences ({selectedProfile.skills.length})</Label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedProfile.skills.slice(0, 20).map((skill, i) => (
                        <Badge key={i} variant="secondary" className="bg-slate-800 text-xs">
                          {skill}
                        </Badge>
                      ))}
                      {selectedProfile.skills.length > 20 && (
                        <Badge variant="outline" className="text-xs">+{selectedProfile.skills.length - 20}</Badge>
                      )}
                    </div>
                  </div>
                )}

                {/* Certifications */}
                {selectedProfile.certifications && selectedProfile.certifications.length > 0 && (
                  <div>
                    <Label className="text-slate-400 text-xs flex items-center gap-1">
                      <Award className="h-3 w-3" />Certifications
                    </Label>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedProfile.certifications.map((cert, i) => (
                        <Badge key={i} variant="outline" className="border-emerald-500/50 text-emerald-400 text-xs">
                          {cert}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Actions */}
                <div className="flex gap-2 pt-2 border-t border-slate-800">
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
