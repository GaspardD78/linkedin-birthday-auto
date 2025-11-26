"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Cake, Search, Square, Loader2, Settings2 } from "lucide-react"
import { useState } from "react"
import { Switch } from "@/components/ui/switch"
import { Label } from "@/components/ui/label"
import { Input } from "@/components/ui/input"

type TaskType = 'birthday' | 'visit' | 'stop'

export function BotControlsWidget() {
  const [loadingTask, setLoadingTask] = useState<TaskType | null>(null);

  // Options pour Anniversaires
  const [birthdayDryRun, setBirthdayDryRun] = useState(true);
  const [processLate, setProcessLate] = useState(false);

  // Options pour Visites
  const [visitDryRun, setVisitDryRun] = useState(true);
  const [visitLimit, setVisitLimit] = useState(10);

  const handleAction = async (action: 'start' | 'stop', jobType?: 'birthday' | 'visit') => {
    const taskType: TaskType = jobType || 'stop';
    setLoadingTask(taskType);

    try {
      let body: any = { action };

      if (jobType === 'birthday') {
        body = {
          action,
          job_type: jobType,
          dry_run: birthdayDryRun,
          process_late: processLate
        };
      } else if (jobType === 'visit') {
        body = {
          action,
          job_type: jobType,
          dry_run: visitDryRun,
          limit: visitLimit
        };
      }

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
          <div className="bg-gradient-to-br from-emerald-600/10 to-emerald-700/10 border border-emerald-600/30 p-4 rounded-lg">
            <div className="flex items-start gap-3 mb-3">
              <div className="text-3xl">🎂</div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1 text-emerald-400">Anniversaires du Jour</h3>
                <p className="text-sm text-slate-300 opacity-90">
                  Vérifie et souhaite les anniversaires du jour
                </p>
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3 mb-3 pl-12 border-l-2 border-emerald-600/30 ml-6">
              <div className="flex items-center justify-between">
                <Label htmlFor="birthday-dry-run" className="text-sm text-slate-300">
                  Mode Test (Dry Run)
                </Label>
                <Switch
                  id="birthday-dry-run"
                  checked={birthdayDryRun}
                  onCheckedChange={setBirthdayDryRun}
                  disabled={loadingTask !== null}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="process-late" className="text-sm text-slate-300">
                  Inclure les retards
                </Label>
                <Switch
                  id="process-late"
                  checked={processLate}
                  onCheckedChange={setProcessLate}
                  disabled={loadingTask !== null}
                />
              </div>
            </div>

            <button
              onClick={() => handleAction('start', 'birthday')}
              disabled={loadingTask !== null}
              className="w-full relative bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-700 hover:to-emerald-800 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 px-4 rounded-md transition-all duration-200 shadow-lg hover:shadow-emerald-500/50 font-semibold"
            >
              {isLoading('birthday') ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  En cours...
                </span>
              ) : (
                'Lancer'
              )}
            </button>
          </div>

          {/* Carte 2 : Visite de Profils */}
          <div className="bg-gradient-to-br from-blue-600/10 to-blue-700/10 border border-blue-600/30 p-4 rounded-lg">
            <div className="flex items-start gap-3 mb-3">
              <div className="text-3xl">🔍</div>
              <div className="flex-1">
                <h3 className="font-bold text-lg mb-1 text-blue-400">Visite de Profils</h3>
                <p className="text-sm text-slate-300 opacity-90">
                  Visite des profils ciblés pour générer des vues
                </p>
              </div>
            </div>

            {/* Options */}
            <div className="space-y-3 mb-3 pl-12 border-l-2 border-blue-600/30 ml-6">
              <div className="flex items-center justify-between">
                <Label htmlFor="visit-dry-run" className="text-sm text-slate-300">
                  Mode Test (Dry Run)
                </Label>
                <Switch
                  id="visit-dry-run"
                  checked={visitDryRun}
                  onCheckedChange={setVisitDryRun}
                  disabled={loadingTask !== null}
                />
              </div>
              <div className="flex items-center justify-between">
                <Label htmlFor="visit-limit" className="text-sm text-slate-300">
                  Nb Profils
                </Label>
                <Input
                  id="visit-limit"
                  type="number"
                  value={visitLimit}
                  onChange={(e) => setVisitLimit(parseInt(e.target.value) || 10)}
                  min={1}
                  max={100}
                  disabled={loadingTask !== null}
                  className="w-20 bg-slate-800 border-slate-700 text-white"
                />
              </div>
            </div>

            <button
              onClick={() => handleAction('start', 'visit')}
              disabled={loadingTask !== null}
              className="w-full relative bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 disabled:opacity-50 disabled:cursor-not-allowed text-white py-2 px-4 rounded-md transition-all duration-200 shadow-lg hover:shadow-blue-500/50 font-semibold"
            >
              {isLoading('visit') ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                  En cours...
                </span>
              ) : (
                'Lancer'
              )}
            </button>
          </div>

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
