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
  auth_available: boolean; // Added for AuthAlert
}

export interface JobStatus {
    job_id: string;
    status: 'queued' | 'started' | 'finished' | 'failed';
    type?: string;
}

// Récupérer les logs via la route API Next.js
export async function getLogs(): Promise<LogEntry[]> {
  try {
    const res = await fetch('/api/logs', { cache: 'no-store' });
    if (!res.ok) return [];

    const data = await res.json();

    if (data.logs && Array.isArray(data.logs)) {
        return data.logs.map((line: string | any) => {
            if (typeof line === 'object') return line;
            let timestamp = new Date().toISOString().split('T')[1].split('.')[0];
            let level = 'INFO';
            let message = line;
            try {
              const match = line.match(/^(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2})?\s*\[?([A-Z]+)\]?\s*(.*)/);
              if (match) {
                 if (match[1]) timestamp = match[1];
                 if (match[2]) level = match[2];
                 if (match[3]) message = match[3];
              }
            } catch (e) { }
            return { timestamp, level, message };
        });
    }
    return [];
  } catch (e) {
    console.error("Error fetching logs:", e);
    return [];
  }
}

export async function getBotStats(): Promise<BotStats> {
  const res = await fetch('/api/stats', { cache: 'no-store' });
  if (!res.ok) throw new Error(`Erreur API : ${res.status} ${res.statusText}`);
  return await res.json();
}

export async function getSystemHealth(): Promise<SystemHealth> {
  try {
    const res = await fetch('/api/system/health', { cache: 'no-store' });
    if (!res.ok) throw new Error("Failed health check");
    const data = await res.json();
    const toBytes = (gb: number) => (gb || 0) * 1024 * 1024 * 1024;

    return {
      cpu_usage: 0,
      memory_usage: {
        total: toBytes(data.totalMemory),
        used: toBytes(data.memoryUsage),
        free: 0
      },
      uptime: data.uptime ? String(data.uptime) : "0",
      temperature: data.cpuTemp || 0,
      auth_available: data.auth_available ?? true // Default true to avoid flash if unknown
    };
  } catch (e) {
    console.error("Health check failed:", e);
    return {
      cpu_usage: 0,
      memory_usage: { total: 1, used: 0, free: 0 },
      uptime: "0",
      temperature: 0,
      auth_available: false
    };
  }
}

// Bot Control & Debug

export async function startBot(type: 'birthday' | 'visit', config: any) {
  const res = await fetch(`/api/bot/start/${type}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!res.ok) {
     const error = await res.json();
     throw new Error(error.detail || 'Failed to start bot');
  }
  return await res.json();
}

export async function stopBot(type?: string, jobId?: string) {
  const body: any = {};
  if (type) body.job_type = type;
  if (jobId) body.job_id = jobId;

  const res = await fetch('/api/bot/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
     const error = await res.json();
     throw new Error(error.detail || 'Failed to stop bot');
  }
  return await res.json();
}

export async function getDebugReport(): Promise<Blob> {
    const res = await fetch('/api/debug/report');
    if (!res.ok) throw new Error("Failed to download report");
    return await res.blob();
}

export async function uploadAuthState(file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/auth/upload', {
        method: 'POST',
        body: formData
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || 'Upload failed');
    return data;
}
