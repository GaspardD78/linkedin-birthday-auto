"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Terminal } from "lucide-react"

export function LogsWidget() {
  const logs = [
    "[10:00:01] System started",
    "[10:00:02] Connected to database",
    "[10:00:05] Bot initialized",
    "[10:05:00] Checking for new tasks...",
    "[10:05:01] No new tasks found"
  ]

  return (
    <Card className="bg-slate-900 border-slate-800 h-full">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200 flex items-center gap-2">
          <Terminal className="h-4 w-4" />
          System Logs
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="bg-slate-950 rounded-md p-4 h-[300px] overflow-y-auto font-mono text-xs text-slate-300 border border-slate-800">
          {logs.map((log, index) => (
            <div key={index} className="mb-1 last:mb-0">
              {log}
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
