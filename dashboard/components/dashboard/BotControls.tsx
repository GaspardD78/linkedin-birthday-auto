"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Play, Square, Pause, Loader2 } from "lucide-react"
import { useState } from "react"

export function BotControlsWidget() {
  const [isLoading, setIsLoading] = useState(false);

  const handleAction = async (action: 'start' | 'stop' | 'pause') => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action }),
      });

      const data = await response.json();

      if (response.ok) {
        alert(`Commande envoyée : ${data.message || 'Succès'}`);
      } else {
        alert(`Erreur : ${data.error || 'Une erreur est survenue'}`);
      }
    } catch (error) {
      alert('Erreur de communication avec le serveur');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium text-slate-200">
          Controls
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => handleAction('start')}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white p-2 rounded-md transition-colors text-sm font-medium"
          >
            {isLoading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
            Start
          </button>

          <button
            onClick={() => handleAction('stop')}
            disabled={isLoading}
            className="flex items-center justify-center gap-2 bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white p-2 rounded-md transition-colors text-sm font-medium"
          >
            <Square className="h-4 w-4" />
            Stop
          </button>

          <button
            disabled={true} // Pause pas encore supporté par le worker
            className="col-span-2 flex items-center justify-center gap-2 bg-slate-800 text-slate-500 p-2 rounded-md cursor-not-allowed text-sm font-medium"
          >
            <Pause className="h-4 w-4" />
            Pause
          </button>
        </div>
      </CardContent>
    </Card>
  )
}
