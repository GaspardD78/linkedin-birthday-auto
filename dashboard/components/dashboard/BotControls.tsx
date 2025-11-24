"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Play, Square, Pause } from "lucide-react"

export function BotControlsWidget() {
  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-slate-200">
          Controls
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          <button className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white p-2 rounded-md transition-colors text-sm font-medium">
            <Play className="h-4 w-4" />
            Start
          </button>
          <button className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 text-white p-2 rounded-md transition-colors text-sm font-medium">
            <Square className="h-4 w-4" />
            Stop
          </button>
          <button className="col-span-2 flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 text-slate-200 p-2 rounded-md transition-colors text-sm font-medium">
            <Pause className="h-4 w-4" />
            Pause
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
