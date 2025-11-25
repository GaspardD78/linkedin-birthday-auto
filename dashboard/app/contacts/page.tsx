"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Search, Filter, Briefcase, MapPin, Calendar, MoreHorizontal, UserPlus } from "lucide-react"
import { useState } from "react"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export default function ContactsPage() {
  const [searchTerm, setSearchTerm] = useState("")

  // Mock data for contacts
  const contacts = [
    {
      id: 1,
      name: "Jean Dupont",
      role: "CTO",
      company: "TechCorp",
      location: "Paris, France",
      status: "connected",
      date: "Nov 24, 2025",
      avatar: "JD"
    },
    {
      id: 2,
      name: "Marie Martin",
      role: "HR Director",
      company: "StartupFlow",
      location: "Lyon, France",
      status: "pending",
      date: "Nov 23, 2025",
      avatar: "MM"
    },
    {
      id: 3,
      name: "Pierre Durand",
      role: "CEO",
      company: "InnovationLab",
      location: "Bordeaux, France",
      status: "connected",
      date: "Nov 22, 2025",
      avatar: "PD"
    },
    {
      id: 4,
      name: "Sophie Bernard",
      role: "Head of Marketing",
      company: "CreativeAgency",
      location: "Marseille, France",
      status: "new",
      date: "Nov 20, 2025",
      avatar: "SB"
    },
    {
      id: 5,
      name: "Lucas Petit",
      role: "Senior Developer",
      company: "WebSolutions",
      location: "Nantes, France",
      status: "connected",
      date: "Nov 18, 2025",
      avatar: "LP"
    }
  ]

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'connected': return 'text-emerald-500 bg-emerald-500/10 border-emerald-500/20';
      case 'pending': return 'text-orange-500 bg-orange-500/10 border-orange-500/20';
      case 'new': return 'text-blue-500 bg-blue-500/10 border-blue-500/20';
      default: return 'text-slate-400 bg-slate-800 border-slate-700';
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-3xl font-bold text-white tracking-tight">Contacts</h1>
          <p className="text-slate-400 text-sm mt-1">Manage your professional network database</p>
        </div>
        <div className="flex gap-2 w-full md:w-auto">
          <Button variant="outline" className="gap-2 border-slate-700 hover:bg-slate-800">
            <Filter className="h-4 w-4" />
            Filter
          </Button>
          <Button className="gap-2 bg-blue-600 hover:bg-blue-700 text-white">
            <UserPlus className="h-4 w-4" />
            Add Contact
          </Button>
        </div>
      </div>

      {/* Main Content */}
      <Card className="bg-slate-900 border-slate-800">
        <CardHeader className="p-4 border-b border-slate-800">
          <div className="relative">
            <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
            <Input
              placeholder="Search contacts by name, company or role..."
              className="pl-9 bg-slate-950 border-slate-800 focus:border-blue-500 text-slate-200"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-slate-500 uppercase bg-slate-950/50 border-b border-slate-800">
                <tr>
                  <th className="px-6 py-3 font-medium">Name</th>
                  <th className="px-6 py-3 font-medium">Role & Company</th>
                  <th className="px-6 py-3 font-medium">Location</th>
                  <th className="px-6 py-3 font-medium">Status</th>
                  <th className="px-6 py-3 font-medium">Added</th>
                  <th className="px-6 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800">
                {contacts.map((contact) => (
                  <tr key={contact.id} className="hover:bg-slate-800/50 transition-colors group">
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="h-8 w-8 rounded-full bg-slate-800 flex items-center justify-center text-xs font-bold text-slate-300 border border-slate-700">
                          {contact.avatar}
                        </div>
                        <span className="font-medium text-slate-200 group-hover:text-blue-400 transition-colors">
                          {contact.name}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-slate-200">{contact.role}</span>
                        <div className="flex items-center gap-1 text-slate-500 text-xs mt-0.5">
                          <Briefcase className="h-3 w-3" />
                          {contact.company}
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-slate-400">
                        <MapPin className="h-3 w-3" />
                        {contact.location}
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-medium border uppercase tracking-wide ${getStatusStyle(contact.status)}`}>
                        {contact.status}
                      </span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1 text-slate-500 text-xs">
                        <Calendar className="h-3 w-3" />
                        {contact.date}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" className="h-8 w-8 p-0 text-slate-500 hover:text-white hover:bg-slate-800">
                            <span className="sr-only">Open menu</span>
                            <MoreHorizontal className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="bg-slate-900 border-slate-800 text-slate-200">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuItem className="focus:bg-slate-800 cursor-pointer">View Profile</DropdownMenuItem>
                          <DropdownMenuItem className="focus:bg-slate-800 cursor-pointer">Send Message</DropdownMenuItem>
                          <DropdownMenuSeparator className="bg-slate-800" />
                          <DropdownMenuItem className="text-red-500 focus:bg-red-900/10 cursor-pointer">Remove Contact</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      <div className="text-center text-xs text-slate-500 mt-4">
        Showing 5 of 128 contacts
      </div>
    </div>
  )
}
