"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Plus, Send, Play, Pause, MoreVertical, BarChart2, Users, Target } from "lucide-react"

export default function CampaignsPage() {
  // Mock data for campaigns
  const campaigns = [
    {
      id: 1,
      name: "CTO Outreach Paris",
      status: "active",
      type: "Connect & Message",
      progress: 65,
      sent: 145,
      replied: 32,
      target: 250,
      startDate: "Nov 20, 2025"
    },
    {
      id: 2,
      name: "HR Directors Follow-up",
      status: "paused",
      type: "Message Only",
      progress: 30,
      sent: 45,
      replied: 8,
      target: 150,
      startDate: "Nov 15, 2025"
    },
    {
      id: 3,
      name: "Startup Founders Network",
      status: "completed",
      type: "Visit & Connect",
      progress: 100,
      sent: 200,
      replied: 58,
      target: 200,
      startDate: "Nov 01, 2025"
    }
  ]

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-emerald-500 hover:bg-emerald-600';
      case 'paused': return 'bg-orange-500 hover:bg-orange-600';
      case 'completed': return 'bg-blue-500 hover:bg-blue-600';
      default: return 'bg-slate-500';
    }
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'active': return 'text-emerald-500 border-emerald-500/30 bg-emerald-500/10';
      case 'paused': return 'text-orange-500 border-orange-500/30 bg-orange-500/10';
      case 'completed': return 'text-blue-500 border-blue-500/30 bg-blue-500/10';
      default: return 'text-slate-500';
    }
  }

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Campagnes</h1>
          <p className="text-slate-400 text-sm mt-1">Orchestrate your automated outreach sequences</p>
        </div>
        <Button className="gap-2 bg-blue-600 hover:bg-blue-700 text-white shadow-lg shadow-blue-900/20">
          <Plus className="h-4 w-4" />
          Create Campaign
        </Button>
      </div>

      {/* Campaign Stats Overview */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-full bg-blue-500/10 text-blue-500">
              <Target className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Active Campaigns</p>
              <h3 className="text-2xl font-bold text-white">3</h3>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-full bg-emerald-500/10 text-emerald-500">
              <Send className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Total Sent</p>
              <h3 className="text-2xl font-bold text-white">390</h3>
            </div>
          </CardContent>
        </Card>
        <Card className="bg-slate-900 border-slate-800">
          <CardContent className="p-6 flex items-center gap-4">
            <div className="p-3 rounded-full bg-purple-500/10 text-purple-500">
              <BarChart2 className="h-6 w-6" />
            </div>
            <div>
              <p className="text-sm text-slate-500 font-medium">Avg. Reply Rate</p>
              <h3 className="text-2xl font-bold text-white">22.5%</h3>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Campaigns List */}
      <div className="grid gap-6">
        {campaigns.map((campaign) => (
          <Card key={campaign.id} className="bg-slate-900 border-slate-800 overflow-hidden hover:border-slate-700 transition-colors">
            <div className="p-6">
              <div className="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
                <div className="flex items-start gap-4">
                  <div className={`mt-1 h-3 w-3 rounded-full ${campaign.status === 'active' ? 'bg-emerald-500 animate-pulse' : campaign.status === 'paused' ? 'bg-orange-500' : 'bg-blue-500'}`} />
                  <div>
                    <h3 className="text-lg font-semibold text-white flex items-center gap-3">
                      {campaign.name}
                      <span className={`text-[10px] px-2 py-0.5 rounded-full border uppercase tracking-wider font-bold ${getStatusBadge(campaign.status)}`}>
                        {campaign.status}
                      </span>
                    </h3>
                    <p className="text-slate-400 text-sm flex items-center gap-2 mt-1">
                      <span className="bg-slate-800 px-2 py-0.5 rounded text-xs">{campaign.type}</span>
                      <span>•</span>
                      <span>Started {campaign.startDate}</span>
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2 w-full md:w-auto">
                  {campaign.status === 'active' ? (
                    <Button variant="outline" size="sm" className="gap-2 border-slate-700 text-orange-400 hover:text-orange-300 hover:bg-slate-800">
                      <Pause className="h-4 w-4" />
                      Pause
                    </Button>
                  ) : (
                    <Button variant="outline" size="sm" className="gap-2 border-slate-700 text-emerald-400 hover:text-emerald-300 hover:bg-slate-800">
                      <Play className="h-4 w-4" />
                      Resume
                    </Button>
                  )}
                  <Button variant="ghost" size="icon" className="text-slate-500 hover:text-white hover:bg-slate-800">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="grid md:grid-cols-12 gap-6 items-center">
                <div className="md:col-span-5 space-y-2">
                  <div className="flex justify-between text-xs mb-1">
                    <span className="text-slate-400">Progress</span>
                    <span className="text-white font-medium">{campaign.progress}%</span>
                  </div>
                  <Progress value={campaign.progress} className="h-2 bg-slate-800" indicatorClassName={getStatusColor(campaign.status)} />
                  <p className="text-xs text-slate-500 text-right">{campaign.sent} / {campaign.target} contacted</p>
                </div>

                <div className="md:col-span-7 grid grid-cols-3 gap-4 border-t md:border-t-0 md:border-l border-slate-800 pt-4 md:pt-0 md:pl-6">
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Sent</p>
                    <p className="text-xl font-bold text-white mt-1">{campaign.sent}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Replied</p>
                    <p className="text-xl font-bold text-white mt-1">{campaign.replied}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500 uppercase tracking-wide">Rate</p>
                    <p className="text-xl font-bold text-emerald-400 mt-1">
                      {Math.round((campaign.replied / campaign.sent) * 100)}%
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>
    </div>
  )
}
