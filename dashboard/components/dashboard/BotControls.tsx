"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cake, Search, Square, Loader2 } from "lucide-react"
import { useState } from "react"

type TaskType = 'birthday' | 'visit' | 'stop'

export function BotControlsWidget() {
  const [loadingTask, setLoadingTask] = useState<TaskType | null>(null);

  const handleAction = async (action: 'start' | 'stop', jobType?: 'birthday' | 'visit') => {
    const taskType: TaskType = jobType || 'stop';
    setLoadingTask(taskType);

    try {
      const body = jobType
        ? { action, job_type: jobType }
        : { action };

      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (response.ok) {
        alert(`✅ Commande envoyée : ${data.message || 'Succès'}`);
      } else {
        alert(`❌ Erreur : ${data.error || 'Une erreur est survenue'}`);
      }
    } catch (error) {
      alert('❌ Erreur de communication avec le serveur');
    } finally {
      setLoadingTask(null);
    }
  };

  const isLoading = (task: TaskType) => loadingTask === task;

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="pb-3">
        <CardTitle className="text-lg font-semibold text-slate-200">
          🎯 Mission Control - Task Runner
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-3">

          {/* Carte 1 : Anniversaires du Jour */}
          <button
            onClick={() => handleAction('start', 'birthday')}
            disabled={loadingTask !== null}
            className="group relative overflow-hidden bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 disabled:opacity-50 disabled:cursor-not-allowed text-white p-4 rounded-lg transition-all duration-200 shadow-lg hover:shadow-emerald-500/50 text-left"
          >
            <div className="flex items-start gap-3">
              <div className="text-3xl">
                {isLoading('birthday') ? <Loader2 className="h-8 w-8 animate-spin" /> : '🎂'}
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1">Anniversaires du Jour</h3>
                <p className="text-sm text-emerald-100 opacity-90">
                  Vérifie et souhaite les anniversaires du jour
                </p>
              </div>
            </div>
            {isLoading('birthday') && (
              <div className="absolute inset-0 bg-emerald-900/30 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-white" />
              </div>
            )}
          </button>

          {/* Carte 2 : Visite de Profils */}
          <button
            onClick={() => handleAction('start', 'visit')}
            disabled={loadingTask !== null}
            className="group relative overflow-hidden bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white p-4 rounded-lg transition-all duration-200 shadow-lg hover:shadow-blue-500/50 text-left"
          >
            <div className="flex items-start gap-3">
              <div className="text-3xl">
                {isLoading('visit') ? <Loader2 className="h-8 w-8 animate-spin" /> : '🔍'}
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1">Visite de Profils</h3>
                <p className="text-sm text-blue-100 opacity-90">
                  Visite des profils ciblés pour générer des vues
                </p>
              </div>
            </div>
            {isLoading('visit') && (
              <div className="absolute inset-0 bg-blue-900/30 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-white" />
              </div>
            )}
          </button>

          {/* Carte 3 : Arrêt d'Urgence */}
          <button
            onClick={() => handleAction('stop')}
            disabled={loadingTask !== null}
            className="group relative overflow-hidden bg-gradient-to-br from-red-600 to-red-700 hover:from-red-700 hover:to-red-800 disabled:opacity-50 disabled:cursor-not-allowed text-white p-4 rounded-lg transition-all duration-200 shadow-lg hover:shadow-red-500/50 text-left border-2 border-red-500"
          >
            <div className="flex items-start gap-3">
              <div className="text-3xl">
                {isLoading('stop') ? <Loader2 className="h-8 w-8 animate-spin" /> : '⏹️'}
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1">Arrêt d'Urgence</h3>
                <p className="text-sm text-red-100 opacity-90">
                  Arrête immédiatement tous les workers actifs
                </p>
              </div>
            </div>
            {isLoading('stop') && (
              <div className="absolute inset-0 bg-red-900/30 flex items-center justify-center">
                <Loader2 className="h-6 w-6 animate-spin text-white" />
              </div>
            )}
          </button>

        </div>
      </CardContent>
    </Card>
  )
}
