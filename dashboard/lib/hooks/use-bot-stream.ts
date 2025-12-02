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
    // Utilisation d'un chemin relatif qui sera géré par le proxy Next.js ou la réécriture
    const url = `/api/stream/events?service=${service}`;
    console.log(`🔌 Connecting to EventStream: ${url}`);

    const eventSource = new EventSource(url);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log("✅ EventStream Connected");
      setConnected(true);
    };

    eventSource.onerror = (err) => {
      console.error("❌ EventStream Error:", err);
      setConnected(false);
      // EventSource tente de se reconnecter automatiquement
    };

    // Écoute des événements de type 'log'
    eventSource.addEventListener('log', (event) => {
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
    });

    // Écoute des événements de type 'status'
    eventSource.addEventListener('status', (event) => {
      try {
        const data = JSON.parse(event.data);
        setStatus(data);
      } catch (e) {
        console.error("Error parsing status event:", e);
      }
    });

    return () => {
      console.log("🔌 Closing EventStream");
      eventSource.close();
      setConnected(false);
    };
  }, [service]);

  const clearLogs = () => setLogs([]);

  return { logs, status, connected, clearLogs };
}
