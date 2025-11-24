"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Send, Clock, CheckCircle2, AlertCircle } from "lucide-react"
import { useState } from "react"

export default function MessagesPage() {
  const [searchTerm, setSearchTerm] = useState("")

  // Mock data for messages
  const messages = [
    {
      id: 1,
      recipient: "Jean Dupont",
      role: "CTO @ TechCorp",
      message: "Bonjour Jean, j'ai vu votre profil et...",
      status: "sent",
      time: "10:30 AM",
      date: "Today"
    },
    {
      id: 2,
      recipient: "Marie Martin",
      role: "HR Director @ StartupFlow",
      message: "Joyeux anniversaire Marie ! J'espère que...",
      status: "queued",
      time: "11:00 AM",
      date: "Today"
    },
    {
      id: 3,
      recipient: "Pierre Durand",
      role: "CEO @ InnovationLab",
      message: "Bonjour Pierre, félicitations pour le nouveau poste...",
      status: "failed",
      time: "Yesterday",
      date: "Nov 23"
    },
    {
      id: 4,
      recipient: "Sophie Bernard",
      role: "Marketing Head @ CreativeAgency",
      message: "Bonjour Sophie, merci pour la connexion...",
      status: "sent",
      time: "Yesterday",
      date: "Nov 23"
    }
  ]

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'sent': return <CheckCircle2 className="h-4 w-4 text-emerald-500" />;
      case 'queued': return <Clock className="h-4 w-4 text-orange-500" />;
      case 'failed': return <AlertCircle className="h-4 w-4 text-red-500" />;
      default: return null;
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'sent': return 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20';
      case 'queued': return 'bg-orange-500/10 text-orange-500 border-orange-500/20';
      case 'failed': return 'bg-red-500/10 text-red-500 border-red-500/20';
      default: return 'bg-slate-800 text-slate-400';
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Messages</h1>
          <p className="text-slate-400 text-sm mt-1">Manage and monitor automated messages</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <Button variant="outline" className="gap-2 border-slate-700 hover:bg-slate-800">
            <Clock className="h-4 w-4" />
            Queue
          </Button>
          <Button className="gap-2 bg-blue-600 hover:bg-blue-700 text-white">
            <Send className="h-4 w-4" />
            New Campaign
          </Button>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-12">
        {/* Messages List */}
        <div className="md:col-span-8 space-y-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader className="p-4 border-b border-slate-800">
              <div className="relative">
                <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
                <Input
                  placeholder="Search messages..."
                  className="pl-9 bg-slate-950 border-slate-800 focus:border-blue-500 text-slate-200"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                />
              </div>
            </CardHeader>
            <CardContent className="p-0">
              <div className="divide-y divide-slate-800">
                {messages.map((msg) => (
                  <div key={msg.id} className="p-4 hover:bg-slate-800/50 transition-colors cursor-pointer group">
                    <div className="flex justify-between items-start mb-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-slate-200 group-hover:text-blue-400 transition-colors">
                          {msg.recipient}
                        </span>
                        <span className={`text-[10px] px-2 py-0.5 rounded-full border ${getStatusColor(msg.status)} uppercase font-medium flex items-center gap-1`}>
                          {getStatusIcon(msg.status)}
                          {msg.status}
                        </span>
                      </div>
                      <span className="text-xs text-slate-500">{msg.time}</span>
                    </div>
                    <p className="text-xs text-slate-400 mb-2">{msg.role}</p>
                    <p className="text-sm text-slate-300 line-clamp-2 leading-relaxed">
                      {msg.message}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Stats & Filters */}
        <div className="md:col-span-4 space-y-4">
          <Card className="bg-slate-900 border-slate-800">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-slate-200">Stats Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-emerald-500/10 rounded-md">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Sent Today</p>
                    <p className="text-lg font-bold text-white">12</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-500/10 rounded-md">
                    <Clock className="h-4 w-4 text-orange-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Queued</p>
                    <p className="text-lg font-bold text-white">5</p>
                  </div>
                </div>
              </div>

              <div className="flex items-center justify-between p-3 bg-slate-950 rounded-lg border border-slate-800">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-500/10 rounded-md">
                    <AlertCircle className="h-4 w-4 text-red-500" />
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">Failed</p>
                    <p className="text-lg font-bold text-white">1</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
