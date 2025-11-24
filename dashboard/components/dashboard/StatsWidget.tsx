"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Users, Mail, Eye } from "lucide-react"

export function StatsWidget() {
  // Static data for now, will connect to API later
  const stats = [
    {
      title: "Messages Sent",
      value: "12",
      icon: Mail,
      description: "+2 from yesterday"
    },
    {
      title: "Profiles Visited",
      value: "45",
      icon: Eye,
      description: "+15 from yesterday"
    },
    {
      title: "Contacts Found",
      value: "128",
      icon: Users,
      description: "+5 from yesterday"
    }
  ]

  return (
    <div className="grid gap-4 md:grid-cols-3">
      {stats.map((stat, index) => (
        <Card key={index} className="bg-slate-900 border-slate-800">
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium text-slate-200">
              {stat.title}
            </CardTitle>
            <stat.icon className="h-4 w-4 text-slate-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-white">{stat.value}</div>
            <p className="text-xs text-slate-500">
              {stat.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
