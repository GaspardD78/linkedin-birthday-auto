import { useState, useEffect, useRef } from 'react';

export interface BotStatus {
  status: 'actif' | 'inactif' | 'en attente' | 'inconnu';
  pending_tasks: number;
  busy_workers: number;
}

interface LogMessage {
  message: string;
  timestamp: string; // Ajouté côté client lors de la réception
}

interface UseBotStreamReturn {
  logs: LogMessage[];
  status: BotStatus;
  connected: boolean;
  clearLogs: () => void;
}

export function useBotStream(service: string = 'worker'): UseBotStreamReturn {
  const [logs, setLogs] = useState<LogMessage[]>([]);
  const [status, setStatus] = useState<BotStatus>({
    status: 'inconnu',
    pending_tasks: 0,
    busy_workers: 0
  });
  const [connected, setConnected] = useState(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    // Nettoyage de l'ancienne connexion si elle existe
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Création de la nouvelle connexion SSE
    const url = `/api/stream/events?service=${service}`;
    console.log(`🔌 Connecting to EventStream: ${url}`);

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    // Définir les handlers avec des références stables pour le nettoyage
    const handleOpen = () => {
      console.log("✅ EventStream Connected");
      setConnected(true);
    };

    const handleError = (err: Event) => {
      console.error("❌ EventStream Error:", err);
      setConnected(false);
      // EventSource tente de se reconnecter automatiquement
    };

    const handleLog = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        const newLog = {
          message: data.message,
          timestamp: new Date().toISOString()
        };

        setLogs(prevLogs => {
          // On garde les 1000 derniers logs pour éviter la surcharge mémoire
          const newLogs = [...prevLogs, newLog];
          if (newLogs.length > 1000) {
            return newLogs.slice(newLogs.length - 1000);
          }
          return newLogs;
        });
      } catch (e) {
        console.error("Error parsing log event:", e);
      }
    };

    const handleStatus = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data);
      } catch (e) {
        console.error("Error parsing status event:", e);
      }
    };

    // Attacher les listeners
    eventSource.onopen = handleOpen;
    eventSource.onerror = handleError;
    eventSource.addEventListener('log', handleLog);
    eventSource.addEventListener('status', handleStatus);

    return () => {
      console.log("🔌 Closing EventStream - Removing listeners");
      // CRITIQUE: Supprimer les listeners AVANT de fermer pour éviter les fuites mémoire
      eventSource.removeEventListener('log', handleLog);
      eventSource.removeEventListener('status', handleStatus);
      eventSource.onopen = null;
      eventSource.onerror = null;
      eventSource.close();
      setConnected(false);
    };
  }, [service]);

  const clearLogs = () => setLogs([]);

  return { logs, status, connected, clearLogs };
}
