"use client"

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Bot, Clock, Inbox } from "lucide-react"

// Définition du type pour les données de statut du worker
interface WorkerStatusData {
  status: 'actif' | 'inactif' | 'en attente' | 'inconnu';
  pending_tasks: number;
  busy_workers: number;
  error?: string;
}

// Fonction pour récupérer le statut du worker depuis l'API
async function fetchWorkerStatus(): Promise<WorkerStatusData> {
  try {
    const response = await fetch('/api/worker/status', { cache: 'no-store' });
    if (!response.ok) {
      // Gérer les erreurs HTTP
      const errorData = await response.json();
      throw new Error(errorData.error || `HTTP error! status: ${response.status}`);
    }
    return await response.json();
  } catch (error) {
    console.error("Failed to fetch worker status:", error);
    // Retourner un état d'erreur clair
    return {
      status: 'inconnu',
      pending_tasks: 0,
      busy_workers: 0,
      error: error instanceof Error ? error.message : "An unknown error occurred",
    };
  }
}

export function BotStatusWidget() {
  const [status, setStatus] = useState<WorkerStatusData>({
    status: 'inconnu',
    pending_tasks: 0,
    busy_workers: 0,
  });

  // Hook pour rafraîchir les données toutes les 5 secondes
  useEffect(() => {
    const fetchData = async () => {
      const data = await fetchWorkerStatus();
      setStatus(data);
    };

    fetchData(); // Appel initial
    const interval = setInterval(fetchData, 5000); // Rafraîchir toutes les 5 secondes

    return () => clearInterval(interval); // Nettoyage de l'intervalle
  }, []);

  // Fonction pour déterminer la couleur en fonction du statut
  const getStatusColor = (state: string) => {
    switch (state) {
      case 'actif': return 'text-blue-500';
      case 'en attente': return 'text-orange-500';
      case 'inactif': return 'text-slate-500';
      default: return 'text-red-500'; // 'inconnu' ou erreur
    }
  };

  const statusText = status.status.charAt(0).toUpperCase() + status.status.slice(1);

  return (
    <Card className="bg-slate-900 border-slate-800">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-slate-200">
          Worker Status
        </CardTitle>
        <Bot className={`h-4 w-4 ${getStatusColor(status.status)}`} />
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-2">
          {/* Statut principal */}
          <div className="flex items-center gap-2">
            <div className={`h-2.5 w-2.5 rounded-full bg-current ${getStatusColor(status.status)}`} />
            <span className="text-2xl font-bold text-white">{statusText}</span>
          </div>

          {/* Tâches en attente */}
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Inbox className="h-3 w-3" />
            <span>Tâches en attente: <strong>{status.pending_tasks}</strong></span>
          </div>

          {/* Workers actifs */}
          <div className="text-xs text-slate-400 flex items-center gap-1.5">
            <Clock className="h-3 w-3" />
            <span>Workers actifs: <strong>{status.busy_workers}</strong></span>
          </div>

          {/* Affichage d'erreur */}
          {status.error && (
            <div className="text-xs text-red-500 mt-1">
              Erreur: {status.error}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
