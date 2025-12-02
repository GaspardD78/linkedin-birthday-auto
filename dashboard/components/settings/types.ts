export interface ConfigData {
  version: string
  dry_run: boolean
  bot_mode: 'standard' | 'unlimited' | 'custom'

  browser: {
    headless: boolean
    slow_mo: [number, number]
    user_agents: string[]
    viewport_sizes: Array<{width: number, height: number}>
    locale: string
    timezone: string
    args: string[] | null
  }

  auth: {
    auth_state_env_var: string
    auth_file_path: string
    auth_fallback_path: string | null
  }

  messaging_limits: {
    max_messages_per_run: number | null
    weekly_message_limit: number
    daily_message_limit: number | null
  }

  scheduling: {
    daily_start_hour: number
    daily_end_hour: number
    timezone: string
  }

  delays: {
    min_delay_seconds: number
    max_delay_seconds: number
    action_delay_min: number
    action_delay_max: number
  }

  messages: {
    messages_file: string
    late_messages_file: string
    avoid_repetition_years: number
  }

  birthday_filter: {
    process_today: boolean
    process_late: boolean
    max_days_late: number
  }

  visitor: {
    enabled: boolean
    keywords: string[]
    location: string
    limits: {
      profiles_per_run: number
      max_pages_to_scrape: number
      max_pages_without_new: number
    }
    delays: {
      min_seconds: number
      max_seconds: number
      profile_visit_min: number
      profile_visit_max: number
      page_navigation_min: number
      page_navigation_max: number
    }
    retry: {
      max_attempts: number
      backoff_factor: number
    }
  }

  proxy: {
    enabled: boolean
    rotation_enabled: boolean
    config_file: string | null
  }

  debug: {
    advanced_debug: boolean
    save_screenshots: boolean
    save_html: boolean
    log_level: 'DEBUG' | 'INFO' | 'WARNING' | 'ERROR' | 'CRITICAL'
  }

  monitoring: {
    enabled: boolean
    prometheus_enabled: boolean
    prometheus_port: number
  }

  database: {
    enabled: boolean
    db_path: string
    timeout: number
  }

  paths: {
    logs_dir: string
    data_dir: string
  }
}
