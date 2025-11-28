export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

export interface BotStats {
  wishes_sent_total: number;
  wishes_sent_today: number;
  wishes_sent_week: number;
  profiles_visited_total: number;
  profiles_visited_today: number;
}

export interface SystemHealth {
  cpu_usage: number;
  memory_usage: {
    total: number;
    used: number;
    free: number;
  };
  uptime: string;
  temperature: number;
}

// Récupérer les logs via la route API Next.js
export async function getLogs(): Promise<LogEntry[]> {
  try {
    // Appel à la route API interne du dashboard qui proxy vers le Python
    const res = await fetch('/api/logs', { cache: 'no-store' });
    if (!res.ok) return [];

    // Adaptation : l'API Python peut renvoyer un JSON ou du texte brut
    const data = await res.json();

    // Si l'API renvoie un objet { logs: [...] }
    if (data.logs && Array.isArray(data.logs)) {
        return data.logs.map((line: string | any) => {
            if (typeof line === 'object') return line;

            // Tentative de parsing plus intelligent
            // Format attendu: "2023-01-01 12:00:00 [INFO] Message"
            let timestamp = new Date().toISOString().split('T')[1].split('.')[0];
            let level = 'INFO';
            let message = line;

            try {
              // Regex pour détecter timestamp et level standards
              const match = line.match(/^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})?\s*\[?([A-Z]+)\]?\s*(.*)/);
              if (match) {
                 if (match[1]) timestamp = match[1];
                 if (match[2]) level = match[2];
                 if (match[3]) message = match[3];
              }
            } catch (e) {
              // Fallback au parsing basique en cas d'échec
            }

            return {
                timestamp,
                level,
                message
            };
        });
    }
    return [];
  } catch (e) {
    console.error("Error fetching logs:", e);
    return [];
  }
}

// Récupérer les statistiques
export async function getBotStats(): Promise<BotStats> {
  // Ne plus masquer les erreurs - les propager au composant
  // pour afficher un message d'erreur visible à l'utilisateur
  const res = await fetch('/api/stats', { cache: 'no-store' });
  if (!res.ok) {
    throw new Error(`Erreur API : ${res.status} ${res.statusText}`);
  }
  return await res.json();
}

// Récupérer la santé du système
export async function getSystemHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch('/api/system/health', { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed health check");
    const data = await res.json();

    // Conversion si nécessaire (l'API renvoie déjà en GB généralement, adapter selon le retour réel)
    // Ici on suppose que l'API renvoie des GB comme vu dans dashboard/app/api/system/health/route.ts
    const toBytes = (gb: number) => (gb || 0) * 1024 * 1024 * 1024;

    return {
      cpu_usage: 0, // Difficile à obtenir sans appel OS spécifique, laissé à 0 ou mock
      memory_usage: {
        total: toBytes(data.totalMemory),
        used: toBytes(data.memoryUsage),
        free: 0
      },
      uptime: data.uptime ? String(data.uptime) : "0",
      temperature: data.cpuTemp || 0
    };
  } catch (e) {
    console.error("Health check failed:", e);
    return {
      cpu_usage: 0,
      memory_usage: { total: 1, used: 0, free: 0 },
      uptime: "0",
      temperature: 0
    };
  }
}
