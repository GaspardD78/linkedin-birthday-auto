/**
 * API client for Automation Scheduler
 *
 * Provides type-safe functions to interact with the scheduler API.
 */

import type {
  ScheduledJob,
  JobExecutionLog,
  CreateJobRequest,
  UpdateJobRequest,
  ToggleJobRequest,
  SchedulerHealthResponse,
  RunJobResponse,
} from '@/types/scheduler';

/**
 * Base API URL for scheduler endpoints.
 */
const SCHEDULER_API_BASE = '/api/scheduler';

/**
 * Generic fetch wrapper with error handling.
 */
async function fetchAPI<T>(
  endpoint: string,
  options?: RequestInit
): Promise<T> {
  const response = await fetch(`${SCHEDULER_API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'API request failed');
  }

  return data as T;
}

// ============================================================================
// Job CRUD Operations
// ============================================================================

/**
 * List all scheduled jobs.
 *
 * @param enabledOnly - If true, only return enabled jobs
 * @returns Array of scheduled jobs
 */
export async function listJobs(
  enabledOnly: boolean = false
): Promise<ScheduledJob[]> {
  const query = enabledOnly ? '?enabled_only=true' : '';
  return fetchAPI<ScheduledJob[]>(`/jobs${query}`);
}

/**
 * Get a specific job by ID.
 *
 * @param jobId - Job identifier
 * @returns Scheduled job
 */
export async function getJob(jobId: string): Promise<ScheduledJob> {
  return fetchAPI<ScheduledJob>(`/jobs/${jobId}`);
}

/**
 * Create a new scheduled job.
 *
 * @param request - Job creation request
 * @returns Created job
 */
export async function createJob(
  request: CreateJobRequest
): Promise<ScheduledJob> {
  return fetchAPI<ScheduledJob>('/jobs', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

/**
 * Update an existing job.
 *
 * @param jobId - Job identifier
 * @param request - Update request (partial)
 * @returns Updated job
 */
export async function updateJob(
  jobId: string,
  request: UpdateJobRequest
): Promise<ScheduledJob> {
  return fetchAPI<ScheduledJob>(`/jobs/${jobId}`, {
    method: 'PUT',
    body: JSON.stringify(request),
  });
}

/**
 * Delete a job.
 *
 * @param jobId - Job identifier
 */
export async function deleteJob(jobId: string): Promise<void> {
  return fetchAPI<void>(`/jobs/${jobId}`, {
    method: 'DELETE',
  });
}

/**
 * Toggle job enabled/disabled state.
 *
 * @param jobId - Job identifier
 * @param enabled - True to enable, false to disable
 * @returns Updated job
 */
export async function toggleJob(
  jobId: string,
  enabled: boolean
): Promise<ScheduledJob> {
  return fetchAPI<ScheduledJob>(`/jobs/${jobId}/toggle`, {
    method: 'POST',
    body: JSON.stringify({ enabled } as ToggleJobRequest),
  });
}

/**
 * Execute a job immediately (outside of schedule).
 *
 * @param jobId - Job identifier
 * @returns Run confirmation
 */
export async function runJobNow(jobId: string): Promise<RunJobResponse> {
  return fetchAPI<RunJobResponse>(`/jobs/${jobId}/run`, {
    method: 'POST',
  });
}

// ============================================================================
// Job History
// ============================================================================

/**
 * Get execution history for a job.
 *
 * @param jobId - Job identifier
 * @param limit - Maximum number of logs to return (1-200)
 * @returns Array of execution logs
 */
export async function getJobHistory(
  jobId: string,
  limit: number = 50
): Promise<JobExecutionLog[]> {
  return fetchAPI<JobExecutionLog[]>(
    `/jobs/${jobId}/history?limit=${limit}`
  );
}

// ============================================================================
// Scheduler Health
// ============================================================================

/**
 * Check scheduler health.
 *
 * @returns Scheduler health status
 */
export async function getSchedulerHealth(): Promise<SchedulerHealthResponse> {
  return fetchAPI<SchedulerHealthResponse>('/health');
}

// ============================================================================
// Batch Operations
// ============================================================================

/**
 * Enable multiple jobs at once.
 *
 * @param jobIds - Array of job identifiers
 * @returns Array of updated jobs
 */
export async function enableJobs(jobIds: string[]): Promise<ScheduledJob[]> {
  return Promise.all(jobIds.map((id) => toggleJob(id, true)));
}

/**
 * Disable multiple jobs at once.
 *
 * @param jobIds - Array of job identifiers
 * @returns Array of updated jobs
 */
export async function disableJobs(jobIds: string[]): Promise<ScheduledJob[]> {
  return Promise.all(jobIds.map((id) => toggleJob(id, false)));
}

/**
 * Delete multiple jobs at once.
 *
 * @param jobIds - Array of job identifiers
 */
export async function deleteJobs(jobIds: string[]): Promise<void> {
  await Promise.all(jobIds.map((id) => deleteJob(id)));
}
