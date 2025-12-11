// Types
export interface BotStatus {
  active: boolean;
  job_id: string | null;
  tasks_queued: number;
}

export interface JobStatus {
  id: string;
  status: string;
  type: string;
  enqueued_at: string;
  started_at?: string;
}

export interface BotStatusDetailed {
  active_jobs: JobStatus[];
  queued_jobs: JobStatus[];
  worker_status: string;
}

export interface LogEntry {
  timestamp: string;
  level: string;
  message: string;
}

// Interface pour logs structlog (format JSON backend)
interface StructlogEntry {
  timestamp?: string;
  event_time?: string;
  level?: string;
  log_level?: string;
  event?: string;
  message?: string;
  msg?: string;
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
  auth_available: boolean;
}

// Helper for fetching
async function get(url: string, headers: Record<string, string> = {}, responseType: 'json' | 'blob' = 'json') {
  const res = await fetch(url, {
    headers,
    credentials: 'same-origin' // Automatically send session cookie
  });

  if (!res.ok) {
     if (res.status === 401) {
         // Notifier user avant redirect
         if (typeof window !== 'undefined') {
             console.error('⚠️  Session expirée, redirection vers login dans 2s...');

             // TODO: Remplacer par toast notification si bibliothèque disponible
             // toast.error('Session expirée, redirection...')

             setTimeout(() => {
                 window.location.href = '/login';
             }, 2000);
         }
         throw new Error('Session expirée');
     }
     const error = await res.json().catch(() => ({ detail: res.statusText }));
     throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return responseType === 'blob' ? res.blob() : res.json();
}

async function post(url: string, body: any, headers: Record<string, string> = {}) {
  const finalHeaders = { 'Content-Type': 'application/json', ...headers };

  const res = await fetch(url, {
    method: 'POST',
    headers: finalHeaders,
    body: JSON.stringify(body),
    credentials: 'same-origin' // Automatically send session cookie
  });

  if (!res.ok) {
      if (res.status === 401) {
         // Notifier user avant redirect
         if (typeof window !== 'undefined') {
             console.error('⚠️  Session expirée, redirection vers login dans 2s...');

             // TODO: Remplacer par toast notification si bibliothèque disponible
             // toast.error('Session expirée, redirection...')

             setTimeout(() => {
                 window.location.href = '/login';
             }, 2000);
         }
         throw new Error('Session expirée');
     }
     const error = await res.json().catch(() => ({ detail: res.statusText }));
     throw new Error(error.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

// --- API Functions ---

// Legacy but useful
export async function getBotStatus(): Promise<BotStatus> {
  return get('/api/worker/status'); // Still used by some widgets?
}

// Granular status
export async function getBotStatusDetailed(): Promise<BotStatusDetailed> {
  return get('/api/bot/status');
}

export async function startBot(options: {
  dryRun?: boolean;
  processLate?: boolean;
  maxDaysLate?: number;
} = {}) {
  return post('/api/bot/action', {
    action: 'start',
    job_type: 'birthday',
    dry_run: options.dryRun ?? true,
    process_late: options.processLate ?? false,
    max_days_late: options.maxDaysLate ?? 10
  });
}

export async function startVisitorBot(options: {
  dryRun?: boolean;
  limit?: number;
} = {}) {
  return post('/api/bot/action', {
    action: 'start',
    job_type: 'visit',
    dry_run: options.dryRun ?? true,
    limit: options.limit ?? 10
  });
}

export async function stopBot(jobType?: string, jobId?: string) {
  return post('/api/bot/action', {
    action: 'stop',
    job_type: jobType,
    job_id: jobId
  });
}

export async function uploadAuthState(file: File) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch('/api/auth/upload', {
    method: 'POST',
    body: formData,
    credentials: 'same-origin' // Automatically send session cookie
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: 'Upload failed' }));
    throw new Error(error.detail || 'Upload failed');
  }
  return res.json();
}

export async function downloadDebugReport() {
    return get('/api/debug/report', {}, 'blob');
}

export async function getLogs(limit: number = 100, service: string = 'worker'): Promise<LogEntry[]> {
    // Using the new /api/logs endpoint on FastAPI which supports 'service' param
    try {
        const data = await get(`/api/logs?limit=${limit}&service=${service}`);
        if (data.logs && Array.isArray(data.logs)) {
             return data.logs.map((line: string) => {
                try {
                    // Tenter de parser JSON (format structlog)
                    const parsed: StructlogEntry = JSON.parse(line);

                    return {
                        timestamp: parsed.timestamp || parsed.event_time || new Date().toISOString(),
                        level: (parsed.level || parsed.log_level || 'INFO').toUpperCase(),
                        message: parsed.event || parsed.message || parsed.msg || line
                    };
                } catch (e) {
                    // Fallback si le log n'est pas JSON (compatibilité avec anciens logs)
                    // Garder le parsing simple pour anciens logs
                    const timestampMatch = line.match(/(\d{4}-\d{2}-\d{2}[T\s]\d{2}:\d{2}:\d{2})/);
                    const levelMatch = line.match(/\b(DEBUG|INFO|WARNING|ERROR|CRITICAL)\b/i);

                    return {
                        timestamp: timestampMatch ? timestampMatch[1] : new Date().toISOString(),
                        level: levelMatch ? levelMatch[1].toUpperCase() : 'INFO',
                        message: line
                    };
                }
             });
        }
        return [];
    } catch (e) {
        console.error("Error fetching logs:", e);
        return [];
    }
}

export async function getBotStats(): Promise<BotStats> {
  return get('/api/stats'); // Maps to FastAPI /stats
}

export async function getSystemHealth(): Promise<SystemHealth> {
    const data = await get('/api/system/health');

    // Also fetch auth status from FastAPI for the alert
    let authAvailable = true;
    try {
        const healthData = await get('/api/health'); // Lightweight check
        authAvailable = healthData.auth_available;
    } catch (e) {}

    const toBytes = (gb: number) => (gb || 0) * 1024 * 1024 * 1024;
    return {
        cpu_usage: data.cpuTemp || 0, // Mapping temp to cpu_usage for visualization if needed, or keeping distinct
        memory_usage: {
            total: toBytes(data.totalMemory),
            used: toBytes(data.memoryUsage),
            free: 0
        },
        uptime: data.uptime,
        temperature: data.cpuTemp,
        auth_available: authAvailable
    };
}

// Automation control
export interface ServiceStatus {
  name: string
  display_name: string
  active: boolean
  enabled: boolean
  status: string
  description: string
}

export interface ServicesStatusResponse {
  services: ServiceStatus[]
  is_systemd_available: boolean
}

export async function getAutomationServicesStatus(): Promise<ServicesStatusResponse> {
  return get('/api/automation/services/status')
}

export async function executeServiceAction(service: string, action: string) {
  return post('/api/automation/services/action', { service, action })
}

// Worker management
export interface WorkerInfo {
  name: string
  state: string
  current_job: string | null
  successful_jobs: number
  failed_jobs: number
  total_working_time: number
}

export interface WorkersStatusResponse {
  workers: WorkerInfo[]
  total_workers: number
}

export async function getWorkersStatus(): Promise<WorkersStatusResponse> {
  return get('/api/automation/workers/status')
}

// --- Campaign API ---

export interface Campaign {
  id: number;
  name: string;
  search_url: string;
  filters: Record<string, any>;
  status: string;
  created_at: string;
  updated_at: string;
  sent?: number; // Optional stats
  replied?: number;
}

export async function getCampaigns(): Promise<Campaign[]> {
  return get('/api/campaigns/');
}

export async function createCampaign(data: { name: string; filters: Record<string, any>; search_url?: string }) {
  return post('/api/campaigns/', data);
}

export async function startCampaign(id: number) {
  return post(`/api/campaigns/${id}/start`, {});
}

export async function deleteCampaign(id: number) {
  const res = await fetch(`/api/campaigns/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Delete failed');
  return res.json();
}
