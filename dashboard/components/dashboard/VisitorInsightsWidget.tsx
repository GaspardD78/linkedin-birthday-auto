"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { Target, TrendingUp, Users, Briefcase } from "lucide-react"
import { useEffect, useState } from "react"
import { getVisitorInsights, type VisitorInsights } from "../../lib/api"

export function VisitorInsightsWidget() {
  const [insights, setInsights] = useState<VisitorInsights | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchInsights = async () => {
      try {
        const data = await getVisitorInsights(30) // Last 30 days
        setInsights(data)
      } catch (error) {
      } finally {
        setLoading(false)
      }
    }

    fetchInsights()
  }, [])

  if (loading || !insights) {
    return (
        <Card className="bg-slate-900 border-slate-800">
            <CardHeader><CardTitle className="text-slate-200">Visitor Insights</CardTitle></CardHeader>
            <CardContent className="h-48 flex items-center justify-center text-slate-500">
                Loading insights...
            </CardContent>
        </Card>
    )
  }

  // Calculate funnel percentages
  const { funnel } = insights
  const conversionRate = funnel.scraped > 0 ? Math.round((funnel.qualified / funnel.scraped) * 100) : 0

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
      {/* KPI Cards */}
      <Card className="bg-slate-900 border-slate-800 col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
            <Target className="h-4 w-4" /> Avg Fit Score
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="text-4xl font-bold text-white">{insights.avg_fit_score}</div>
            <div className="flex-1 space-y-1">
                <Progress value={insights.avg_fit_score} className="h-2 bg-slate-800" />
                <p className="text-xs text-slate-500">Target: > 70</p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="bg-slate-900 border-slate-800 col-span-2">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
            <Briefcase className="h-4 w-4" /> Open To Work
          </CardTitle>
        </CardHeader>
        <CardContent>
            <div className="text-4xl font-bold text-green-400">{insights.open_to_work_count}</div>
            <p className="text-xs text-slate-500 mt-1">Profiles explicitly looking for opportunities</p>
        </CardContent>
      </Card>

      {/* Funnel */}
      <Card className="bg-slate-900 border-slate-800 col-span-3">
        <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-slate-400 flex items-center gap-2">
                <TrendingUp className="h-4 w-4" /> Conversion Funnel
            </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
            <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Visited</span>
                <span className="text-slate-500">{funnel.visited}</span>
            </div>
            <div className="relative pt-1">
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-slate-800">
                    <div style={{ width: "100%" }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-600"></div>
                </div>
            </div>

            <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Scraped</span>
                <span className="text-slate-500">{funnel.scraped}</span>
            </div>
             <div className="relative pt-1">
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-slate-800">
                    <div style={{ width: `${(funnel.scraped / (funnel.visited || 1)) * 100}%` }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500"></div>
                </div>
            </div>

            <div className="flex justify-between items-center text-sm">
                <span className="text-slate-300">Qualified (&gt;70)</span>
                <span className="text-green-400 font-bold">{funnel.qualified} ({conversionRate}%)</span>
            </div>
             <div className="relative pt-1">
                <div className="overflow-hidden h-2 mb-4 text-xs flex rounded bg-slate-800">
                    <div style={{ width: `${(funnel.qualified / (funnel.visited || 1)) * 100}%` }} className="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-green-500"></div>
                </div>
            </div>
        </CardContent>
      </Card>

      {/* Top Skills */}
      <Card className="bg-slate-900 border-slate-800 col-span-7">
        <CardHeader>
            <CardTitle className="text-sm font-medium text-slate-400">Top Detected Skills</CardTitle>
        </CardHeader>
        <CardContent>
            <div className="flex flex-wrap gap-2">
                {insights.top_skills.map((skill, i) => (
                    <div key={i} className="bg-slate-800 text-slate-200 px-3 py-1 rounded-full text-sm flex items-center gap-2 border border-slate-700">
                        <span>{skill.name}</span>
                        <span className="bg-slate-700 text-xs px-2 py-0.5 rounded-full text-slate-400">{skill.count}</span>
                    </div>
                ))}
                {insights.top_skills.length === 0 && (
                    <p className="text-slate-500 text-sm italic">No skills data available yet.</p>
                )}
            </div>
        </CardContent>
      </Card>
    </div>
  )
}
