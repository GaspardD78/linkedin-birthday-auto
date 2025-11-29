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
        console.log('🎂 [FRONTEND] Envoi Birthday Bot:', body);
      } else if (jobType === 'visit') {
        body = {
          action,
          job_type: jobType,
          dry_run: visitDryRun,
          limit: visitLimit
        };
        console.log('🔍 [FRONTEND] Envoi Visitor Bot:', body);
      } else if (action === 'stop') {
        console.log('🛑 [FRONTEND] Envoi Stop:', body);
      }

      const response = await fetch('/api/bot/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      const data = await response.json();

      if (response.ok) {
        console.log('✅ [FRONTEND] Succès:', data);
        alert(`✅ Commande envoyée : ${data.message || 'Succès'}`);
      } else {
        console.error('❌ [FRONTEND] Erreur API:', data);
        alert(`❌ Erreur : ${data.error || 'Une erreur est survenue'}`);
      }
    } catch (error) {
      console.error('❌ [FRONTEND] Erreur fatale:', error);
      alert('❌ Erreur de communication avec le serveur');
    } finally {
      setLoadingTask(null);
    }
  };

  const isLoading = (task: TaskType) => loadingTask === task;

  return (
    <Card className="bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 border-slate-700 shadow-2xl">
      <CardHeader className="pb-4 border-b border-slate-700/50">
        <div className="flex items-center justify-between">
          <CardTitle className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center shadow-lg shadow-emerald-500/30">
              <Settings2 className="h-5 w-5 text-white" />
            </div>
            Contrôle des Scripts
          </CardTitle>
          <div className="flex items-center gap-2">
            <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
            <span className="text-xs text-slate-400">Prêt</span>
          </div>
        </div>
        <p className="text-sm text-slate-400 mt-2 ml-13">
          Lancez et gérez vos scripts LinkedIn depuis ce panneau de contrôle
        </p>
      </CardHeader>
      <CardContent className="pt-6">
        <div className="grid grid-cols-1 gap-4">

          {/* Carte 1 : Anniversaires du Jour */}
          <div className="relative bg-gradient-to-br from-emerald-600/20 to-emerald-700/10 border-2 border-emerald-600/40 p-5 rounded-xl overflow-hidden group hover:border-emerald-500/60 transition-all duration-300">
            <div className="absolute top-0 right-0 w-32 h-32 bg-emerald-500/10 rounded-full blur-3xl" />
            <div className="relative flex items-start gap-4 mb-4">
              <div className="text-4xl">🎂</div>
              <div className="flex-1">
                <h3 className="font-bold text-xl mb-1 text-emerald-300">Anniversaires du Jour</h3>
                <p className="text-sm text-slate-300">
                  Vérifie et souhaite les anniversaires du jour
                </p>
              </div>
            </div>

            {/* Options */}
            <div className="relative space-y-3 mb-4 bg-slate-800/30 rounded-lg p-4 border border-emerald-600/20">
              <div className="flex items-center justify-between">
                <Label htmlFor="birthday-dry-run" className="text-sm text-slate-200 font-medium flex items-center gap-2">
                  <span className="text-xs">🧪</span>
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
                <Label htmlFor="process-late" className="text-sm text-slate-200 font-medium flex items-center gap-2">
                  <span className="text-xs">⏰</span>
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
              className="w-full relative bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 px-6 rounded-lg transition-all duration-200 shadow-lg hover:shadow-emerald-500/50 font-bold text-lg group"
            >
              {isLoading('birthday') ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Lancement en cours...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Cake className="h-5 w-5 group-hover:scale-110 transition-transform" />
                  Lancer le Script
                </span>
              )}
            </button>
          </div>

          {/* Carte 2 : Visite de Profils */}
          <div className="relative bg-gradient-to-br from-blue-600/20 to-blue-700/10 border-2 border-blue-600/40 p-5 rounded-xl overflow-hidden group hover:border-blue-500/60 transition-all duration-300">
            <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 rounded-full blur-3xl" />
            <div className="relative flex items-start gap-4 mb-4">
              <div className="text-4xl">🔍</div>
              <div className="flex-1">
                <h3 className="font-bold text-xl mb-1 text-blue-300">Visite de Profils</h3>
                <p className="text-sm text-slate-300">
                  Visite des profils ciblés pour générer des vues
                </p>
              </div>
            </div>

            {/* Options */}
            <div className="relative space-y-3 mb-4 bg-slate-800/30 rounded-lg p-4 border border-blue-600/20">
              <div className="flex items-center justify-between">
                <Label htmlFor="visit-dry-run" className="text-sm text-slate-200 font-medium flex items-center gap-2">
                  <span className="text-xs">🧪</span>
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
                <Label htmlFor="visit-limit" className="text-sm text-slate-200 font-medium flex items-center gap-2">
                  <span className="text-xs">👥</span>
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
                  className="w-24 bg-slate-800 border-slate-600 text-white font-semibold text-center"
                />
              </div>
            </div>

            <button
              onClick={() => handleAction('start', 'visit')}
              disabled={loadingTask !== null}
              className="w-full relative bg-gradient-to-br from-blue-600 to-blue-700 hover:from-blue-500 hover:to-blue-600 disabled:opacity-50 disabled:cursor-not-allowed text-white py-3 px-6 rounded-lg transition-all duration-200 shadow-lg hover:shadow-blue-500/50 font-bold text-lg group"
            >
              {isLoading('visit') ? (
                <span className="flex items-center justify-center gap-2">
                  <Loader2 className="h-5 w-5 animate-spin" />
                  Lancement en cours...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Search className="h-5 w-5 group-hover:scale-110 transition-transform" />
                  Lancer le Script
                </span>
              )}
            </button>
          </div>

          {/* Carte 3 : Arrêt d'Urgence */}
          <button
            onClick={() => handleAction('stop')}
            disabled={loadingTask !== null}
            className="group relative overflow-hidden bg-gradient-to-br from-red-600/90 to-red-700/90 hover:from-red-600 hover:to-red-700 disabled:opacity-50 disabled:cursor-not-allowed text-white p-6 rounded-xl transition-all duration-200 shadow-2xl hover:shadow-red-500/50 text-left border-2 border-red-500/70 hover:border-red-400"
          >
            <div className="absolute top-0 right-0 w-32 h-32 bg-red-400/20 rounded-full blur-3xl" />
            <div className="relative flex items-start gap-4">
              <div className="text-4xl">
                {isLoading('stop') ? <Loader2 className="h-10 w-10 animate-spin" /> : '⛔'}
              </div>
              <div className="flex-1">
                <h3 className="font-bold text-2xl mb-2 flex items-center gap-2">
                  Arrêt d'Urgence
                  {!isLoading('stop') && <Square className="h-5 w-5" />}
                </h3>
                <p className="text-sm text-red-100">
                  Arrête immédiatement tous les workers actifs et annule les tâches en cours
                </p>
              </div>
            </div>
            {isLoading('stop') && (
              <div className="absolute inset-0 bg-red-900/50 flex items-center justify-center backdrop-blur-sm">
                <div className="flex flex-col items-center gap-2">
                  <Loader2 className="h-8 w-8 animate-spin text-white" />
                  <span className="text-sm font-semibold">Arrêt en cours...</span>
                </div>
              </div>
            )}
          </button>

        </div>
      </CardContent>
    </Card>
  )
}
