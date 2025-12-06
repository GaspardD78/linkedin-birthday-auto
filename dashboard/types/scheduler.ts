/**
 * TypeScript types for Automation Scheduler
 *
 * These types mirror the Python Pydantic models from:
 * - src/scheduler/models.py
 * - src/api/routes/scheduler_routes.py
 */

// ============================================================================
// Enums
// ============================================================================

/**
 * Bot types available for scheduling.
 *
 * Note: There is NO separate "unlimited" bot type.
 * Birthday bot uses the `process_late` flag for late birthday processing.
 */
export enum BotType {
  BIRTHDAY = 'birthday',
  VISITOR = 'visitor',
}

/**
 * Schedule types for job execution.
 */
export enum ScheduleType {
  DAILY = 'daily',
  WEEKLY = 'weekly',
  INTERVAL = 'interval',
  CRON = 'cron',
}

/**
 * Job execution status.
 */
export enum JobStatus {
  SUCCESS = 'success',
  FAILED = 'failed',
  RUNNING = 'running',
  QUEUED = 'queued',
}

// ============================================================================
// Schedule Configurations
// ============================================================================

/**
 * Daily schedule configuration.
 * Executes at a specific time every day.
 */
export interface DailyScheduleConfig {
  hour: number;        // 0-23
  minute: number;      // 0-59
}

/**
 * Weekly schedule configuration.
 * Executes on specific days of the week.
 */
export interface WeeklyScheduleConfig {
  hour: number;
  minute: number;
  day_of_week: string;  // e.g., "mon", "mon,wed,fri", "0-4"
}

/**
 * Interval schedule configuration.
 * Executes at regular intervals.
 */
export interface IntervalScheduleConfig {
  hours: number;
  minutes: number;
}

/**
 * Cron schedule configuration.
 * Advanced cron expression support.
 */
export interface CronScheduleConfig {
  cron_expression: string;  // e.g., "0 8-18 * * 1-5"
}

/**
 * Union type for all schedule configurations.
 */
export type ScheduleConfig =
  | DailyScheduleConfig
  | WeeklyScheduleConfig
  | IntervalScheduleConfig
  | CronScheduleConfig;

// ============================================================================
// Bot Configurations
// ============================================================================

/**
 * Birthday Bot configuration.
 *
 * Key changes from original plan:
 * - No separate "unlimited" mode
 * - Use `process_late` flag to enable late birthday processing
 * - `dry_run` defaults to FALSE (production mode)
 */
export interface BirthdayBotConfig {
  dry_run: boolean;                 // Default: false (production mode)
  process_late: boolean;            // Enable late birthday processing
  max_days_late: number;            // Max days to go back (1-365)
  max_messages_per_run?: number;    // Optional limit per execution
}

/**
 * Visitor Bot configuration.
 */
export interface VisitorBotConfig {
  dry_run: boolean;    // Default: false (production mode)
  limit: number;       // Profiles to visit per execution (1-500)
}

/**
 * Union type for all bot configurations.
 */
export type BotConfig = BirthdayBotConfig | VisitorBotConfig;

// ============================================================================
// Scheduled Job
// ============================================================================

/**
 * Complete scheduled job configuration.
 * Corresponds to ScheduledJobConfig in Python.
 */
export interface ScheduledJob {
  // Identity
  id: string;
  name: string;
  description?: string;
  bot_type: BotType;

  // Activation
  enabled: boolean;

  // Scheduling
  schedule_type: ScheduleType;
  schedule_config: ScheduleConfig;

  // Bot configuration
  bot_config: BotConfig;

  // Metadata
  created_at: string;      // ISO 8601
  updated_at: string;      // ISO 8601
  created_by?: string;

  // Execution state
  last_run_at?: string;         // ISO 8601
  last_run_status?: string;     // "success" | "failed" | "running"
  last_run_error?: string;
  next_run_at?: string;         // ISO 8601

  // APScheduler options
  max_instances?: number;
  misfire_grace_time?: number;
  coalesce?: boolean;
}

// ============================================================================
// Job Execution Log
// ============================================================================

/**
 * Execution log for a scheduled job.
 * Tracks history of job runs.
 */
export interface JobExecutionLog {
  id: string;
  job_id: string;
  started_at: string;              // ISO 8601
  finished_at?: string;            // ISO 8601
  status: JobStatus;
  result?: Record<string, any>;
  error?: string;
  messages_sent: number;
  profiles_visited: number;
}

// ============================================================================
// API Request/Response Types
// ============================================================================

/**
 * Request to create a new scheduled job.
 */
export interface CreateJobRequest {
  name: string;
  description?: string;
  bot_type: BotType;
  enabled?: boolean;
  schedule_type: ScheduleType;
  schedule_config: ScheduleConfig;
  bot_config: BotConfig;
}

/**
 * Request to update an existing job.
 * All fields are optional (partial updates supported).
 */
export interface UpdateJobRequest {
  name?: string;
  description?: string;
  enabled?: boolean;
  schedule_type?: ScheduleType;
  schedule_config?: ScheduleConfig;
  bot_config?: BotConfig;
}

/**
 * Request to toggle job enabled/disabled.
 */
export interface ToggleJobRequest {
  enabled: boolean;
}

/**
 * Response from scheduler health check.
 */
export interface SchedulerHealthResponse {
  status: string;              // "healthy" | "degraded" | "unhealthy"
  scheduler_running: boolean;
  redis_connected: boolean;
  total_jobs: number;
  enabled_jobs: number;
}

/**
 * Response when running a job immediately.
 */
export interface RunJobResponse {
  message: string;
  status: string;  // "queued"
}

// ============================================================================
// UI Helper Types
// ============================================================================

/**
 * Job with typed bot_config for Birthday Bot.
 */
export interface BirthdayJob extends Omit<ScheduledJob, 'bot_config'> {
  bot_type: BotType.BIRTHDAY;
  bot_config: BirthdayBotConfig;
}

/**
 * Job with typed bot_config for Visitor Bot.
 */
export interface VisitorJob extends Omit<ScheduledJob, 'bot_config'> {
  bot_type: BotType.VISITOR;
  bot_config: VisitorBotConfig;
}

/**
 * Type guard to check if job is a Birthday job.
 */
export function isBirthdayJob(job: ScheduledJob): job is BirthdayJob {
  return job.bot_type === BotType.BIRTHDAY;
}

/**
 * Type guard to check if job is a Visitor job.
 */
export function isVisitorJob(job: ScheduledJob): job is VisitorJob {
  return job.bot_type === BotType.VISITOR;
}

// ============================================================================
// Form Types (for React components)
// ============================================================================

/**
 * Form values for creating/editing a job.
 * Used with react-hook-form.
 */
export interface JobFormValues {
  name: string;
  description?: string;
  bot_type: BotType;
  enabled: boolean;
  schedule_type: ScheduleType;

  // Schedule config fields (conditionally rendered)
  daily_hour?: number;
  daily_minute?: number;
  weekly_hour?: number;
  weekly_minute?: number;
  weekly_days?: string;
  interval_hours?: number;
  interval_minutes?: number;
  cron_expression?: string;

  // Birthday bot config
  birthday_dry_run?: boolean;
  birthday_process_late?: boolean;
  birthday_max_days_late?: number;
  birthday_max_messages?: number;

  // Visitor bot config
  visitor_dry_run?: boolean;
  visitor_limit?: number;
}

/**
 * Convert JobFormValues to CreateJobRequest.
 */
export function formValuesToCreateRequest(
  values: JobFormValues
): CreateJobRequest {
  // Build schedule_config
  let schedule_config: ScheduleConfig;

  switch (values.schedule_type) {
    case ScheduleType.DAILY:
      schedule_config = {
        hour: values.daily_hour ?? 8,
        minute: values.daily_minute ?? 0,
      };
      break;

    case ScheduleType.WEEKLY:
      schedule_config = {
        hour: values.weekly_hour ?? 8,
        minute: values.weekly_minute ?? 0,
        day_of_week: values.weekly_days ?? 'mon',
      };
      break;

    case ScheduleType.INTERVAL:
      schedule_config = {
        hours: values.interval_hours ?? 1,
        minutes: values.interval_minutes ?? 0,
      };
      break;

    case ScheduleType.CRON:
      schedule_config = {
        cron_expression: values.cron_expression ?? '0 8 * * *',
      };
      break;

    default:
      throw new Error(`Unknown schedule type: ${values.schedule_type}`);
  }

  // Build bot_config
  let bot_config: BotConfig;

  if (values.bot_type === BotType.BIRTHDAY) {
    bot_config = {
      dry_run: values.birthday_dry_run ?? false,
      process_late: values.birthday_process_late ?? false,
      max_days_late: values.birthday_max_days_late ?? 7,
      max_messages_per_run: values.birthday_max_messages,
    };
  } else if (values.bot_type === BotType.VISITOR) {
    bot_config = {
      dry_run: values.visitor_dry_run ?? false,
      limit: values.visitor_limit ?? 50,
    };
  } else {
    throw new Error(`Unknown bot type: ${values.bot_type}`);
  }

  return {
    name: values.name,
    description: values.description,
    bot_type: values.bot_type,
    enabled: values.enabled,
    schedule_type: values.schedule_type,
    schedule_config,
    bot_config,
  };
}

/**
 * Convert ScheduledJob to JobFormValues (for editing).
 */
export function jobToFormValues(job: ScheduledJob): JobFormValues {
  const values: JobFormValues = {
    name: job.name,
    description: job.description,
    bot_type: job.bot_type,
    enabled: job.enabled,
    schedule_type: job.schedule_type,
  };

  // Extract schedule config
  const sc = job.schedule_config;

  if (job.schedule_type === ScheduleType.DAILY) {
    const daily = sc as DailyScheduleConfig;
    values.daily_hour = daily.hour;
    values.daily_minute = daily.minute;
  } else if (job.schedule_type === ScheduleType.WEEKLY) {
    const weekly = sc as WeeklyScheduleConfig;
    values.weekly_hour = weekly.hour;
    values.weekly_minute = weekly.minute;
    values.weekly_days = weekly.day_of_week;
  } else if (job.schedule_type === ScheduleType.INTERVAL) {
    const interval = sc as IntervalScheduleConfig;
    values.interval_hours = interval.hours;
    values.interval_minutes = interval.minutes;
  } else if (job.schedule_type === ScheduleType.CRON) {
    const cron = sc as CronScheduleConfig;
    values.cron_expression = cron.cron_expression;
  }

  // Extract bot config
  if (job.bot_type === BotType.BIRTHDAY) {
    const bc = job.bot_config as BirthdayBotConfig;
    values.birthday_dry_run = bc.dry_run;
    values.birthday_process_late = bc.process_late;
    values.birthday_max_days_late = bc.max_days_late;
    values.birthday_max_messages = bc.max_messages_per_run;
  } else if (job.bot_type === BotType.VISITOR) {
    const bc = job.bot_config as VisitorBotConfig;
    values.visitor_dry_run = bc.dry_run;
    values.visitor_limit = bc.limit;
  }

  return values;
}

// ============================================================================
// Display Helpers
// ============================================================================

/**
 * Format schedule for display.
 */
export function formatSchedule(job: ScheduledJob): string {
  const { schedule_type, schedule_config } = job;

  if (schedule_type === ScheduleType.DAILY) {
    const config = schedule_config as DailyScheduleConfig;
    return `Quotidien à ${String(config.hour).padStart(2, '0')}:${String(config.minute).padStart(2, '0')}`;
  }

  if (schedule_type === ScheduleType.WEEKLY) {
    const config = schedule_config as WeeklyScheduleConfig;
    return `${config.day_of_week} à ${String(config.hour).padStart(2, '0')}:${String(config.minute).padStart(2, '0')}`;
  }

  if (schedule_type === ScheduleType.INTERVAL) {
    const config = schedule_config as IntervalScheduleConfig;
    return `Toutes les ${config.hours}h ${config.minutes}m`;
  }

  if (schedule_type === ScheduleType.CRON) {
    const config = schedule_config as CronScheduleConfig;
    return config.cron_expression;
  }

  return 'Non planifié';
}

/**
 * Get bot mode display string.
 */
export function getBotModeDisplay(job: ScheduledJob): string {
  if (job.bot_type === BotType.BIRTHDAY) {
    const config = job.bot_config as BirthdayBotConfig;
    if (config.process_late) {
      return `Standard + Retards (${config.max_days_late}j)`;
    }
    return 'Standard';
  }

  if (job.bot_type === BotType.VISITOR) {
    const config = job.bot_config as VisitorBotConfig;
    return `${config.limit} profils/run`;
  }

  return '';
}

/**
 * Get dry-run badge text and color.
 */
export function getDryRunBadge(job: ScheduledJob): {
  text: string;
  variant: 'default' | 'destructive' | 'outline' | 'secondary';
  emoji: string;
} {
  const config = job.bot_config as BirthdayBotConfig | VisitorBotConfig;

  if (config.dry_run) {
    return {
      text: 'Test Mode',
      variant: 'outline',
      emoji: '🧪',
    };
  }

  return {
    text: 'Production',
    variant: 'destructive',
    emoji: '🚀',
  };
}
