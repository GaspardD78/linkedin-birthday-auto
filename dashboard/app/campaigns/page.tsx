"use client"

import { useEffect, useState } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Plus, Send, Play, Pause, Trash2, BarChart2, Target, Loader2 } from "lucide-react"
import { getCampaigns, createCampaign, startCampaign, deleteCampaign, Campaign } from "@/lib/api"
import { toast } from "sonner"

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([])
  const [loading, setLoading] = useState(true)
  const [isCreateOpen, setIsCreateOpen] = useState(false)

  // Form State
  const [newCampaignName, setNewCampaignName] = useState("")
  const [newCampaignKeywords, setNewCampaignKeywords] = useState("")
  const [newCampaignLocation, setNewCampaignLocation] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const fetchCampaigns = async () => {
    try {
      const data = await getCampaigns()
      setCampaigns(data)
    } catch (error) {
      toast.error("Failed to load campaigns")
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCampaigns()
  }, [])

  const handleCreate = async () => {
    if (!newCampaignName || !newCampaignKeywords) {
      toast.error("Name and Keywords are required")
      return
    }

    setIsSubmitting(true)
    try {
      await createCampaign({
        name: newCampaignName,
        filters: {
          keywords: newCampaignKeywords.split(",").map(k => k.trim()),
          location: newCampaignLocation,
          limit: 10 // Default limit
        }
      })
      toast.success("Campaign created")
      setIsCreateOpen(false)
      setNewCampaignName("")
      setNewCampaignKeywords("")
      setNewCampaignLocation("")
      fetchCampaigns()
    } catch (error) {
      toast.error("Failed to create campaign")
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleStart = async (id: number) => {
    try {
      await startCampaign(id)
      toast.success("Campaign started")
      fetchCampaigns() // Refresh status
    } catch (error) {
      toast.error("Failed to start campaign")
    }
  }

  const handleDelete = async (id: number) => {
    if(!confirm("Are you sure? This will delete all campaign data.")) return;
    try {
      await deleteCampaign(id)
      toast.success("Campaign deleted")
      fetchCampaigns()
    } catch (error) {
      toast.error("Failed to delete campaign")
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'bg-emerald-500 hover:bg-emerald-600';
      case 'paused': return 'bg-orange-500 hover:bg-orange-600';
      case 'completed': return 'bg-blue-500 hover:bg-blue-600';
      default: return 'bg-slate-500';
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'running': return 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10';
      case 'paused': return 'text-orange-500 border-orange-500/30 bg-orange-500/10';
      case 'completed': return 'text-blue-500 border-blue-500/30 bg-blue-500/10';
      default: return 'text-slate-500 border-slate-500/30 bg-slate-500/10';
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Campagnes</h1>
          <p className="text-slate-400 text-sm mt-1">Gérez vos campagnes de prospection LinkedIn</p>
        </div>

        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/20">
              <Plus className="h-4 w-4" />
              Nouvelle Campagne
            </Button>
          </DialogTrigger>
          <DialogContent className="bg-slate-900 border-slate-800 text-white">
            <DialogHeader>
              <DialogTitle>Créer une campagne</DialogTitle>
              <DialogDescription>Configurez votre cible pour le visiteur de profils.</DialogDescription>
            </DialogHeader>
            <div className="grid gap-4 py-4">
              <div className="grid gap-2">
                <Label htmlFor="name">Nom</Label>
                <Input id="name" value={newCampaignName} onChange={(e) => setNewCampaignName(e.target.value)} placeholder="Ex: CTO Paris" className="bg-slate-800 border-slate-700" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="keywords">Mots-clés (séparés par virgule)</Label>
                <Input id="keywords" value={newCampaignKeywords} onChange={(e) => setNewCampaignKeywords(e.target.value)} placeholder="Ex: CTO, Directeur Technique" className="bg-slate-800 border-slate-700" />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="location">Localisation</Label>
                <Input id="location" value={newCampaignLocation} onChange={(e) => setNewCampaignLocation(e.target.value)} placeholder="Ex: Paris, France" className="bg-slate-800 border-slate-700" />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsCreateOpen(false)} className="border-slate-700 text-white hover:bg-slate-800">Annuler</Button>
              <Button onClick={handleCreate} disabled={isSubmitting} className="bg-blue-600 hover:bg-blue-700">
                {isSubmitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Créer"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {/* Campaign Stats Overview - Placeholder for now */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
              <Target className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Campagnes</p>
              <h3 className="text-2xl font-bold text-white">{campaigns.length}</h3>
            </div>
          </CardContent>
        </Card>
        {/* More stats can be added here fetching from API */}
      </div>

      {/* Campaigns List */}
      <div className="grid gap-6">
        {loading ? (
            <div className="text-center text-slate-500 py-10">Chargement...</div>
        ) : campaigns.length === 0 ? (
            <div className="text-center text-slate-500 py-10">Aucune campagne. Créez-en une pour commencer !</div>
        ) : (
          campaigns.map((campaign) => (
            <Card key={campaign.id} className="bg-slate-900 border-slate-800 overflow-hidden hover:border-slate-700 transition-colors">
              <div className="p-6">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                  <div className="flex items-start gap-4">
                    <div className={`mt-1 h-3 w-3 rounded-full ${campaign.status === 'running' ? 'bg-emerald-500 animate-pulse' : 'bg-slate-500'}`} />
                    <div>
                      <h3 className="text-lg font-semibold text-white flex items-center gap-3">
                        {campaign.name}
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-bold ${getStatusBadge(campaign.status)}`}>
                          {campaign.status}
                        </span>
                      </h3>
                      <p className="text-slate-400 text-sm flex items-center gap-2 mt-1">
                        <Badge variant="secondary" className="bg-slate-800 text-slate-300 hover:bg-slate-800">
                           {campaign.filters.keywords?.join(", ")}
                        </Badge>
                        <span>•</span>
                        <span>{campaign.filters.location}</span>
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 w-full md:w-auto">
                    {campaign.status !== 'running' && (
                      <Button onClick={() => handleStart(campaign.id)} variant="outline" size="sm" className="gap-2 border-slate-700 text-emerald-400 hover:text-emerald-300 hover:bg-slate-800">
                        <Play className="h-4 w-4" />
                        Lancer (Worker)
                      </Button>
                    )}

                    <Button onClick={() => handleDelete(campaign.id)} variant="ghost" size="icon" className="text-slate-500 hover:text-red-400 hover:bg-slate-800">
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))
        )}
      </div>
    </div>
  )
}
