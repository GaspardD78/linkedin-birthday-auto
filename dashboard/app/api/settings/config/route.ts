import { NextResponse } from 'next/server';
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config';

/**
 * GET /api/settings/config
 *
 * Fetches and parses the YAML configuration from the backend
 * Returns structured JSON configuration for birthday and visitor bots
 * This moves YAML parsing from client-side to server-side for better performance
 */
export async function GET() {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const apiUrl = getApiUrl();

    // Fetch raw YAML from backend
    const response = await fetch(`${apiUrl}/config/yaml`, {
      method: 'GET',
      headers: {
        'X-API-Key': getApiKey()!
      }
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    const data = await response.json();

    // Import js-yaml server-side only
    const yaml = await import('js-yaml');
    const config: any = yaml.load(data.content);

    // Parse and structure the configuration
    const structuredConfig = {
      birthday: {
        max_per_day: config.messaging_limits?.daily_message_limit || 50,
        schedule_time: `${String(config.scheduling?.daily_start_hour || 7).padStart(2, '0')}:30`,
        auto_run_enabled: false, // TODO: Store in database or Redis
        mode: config.bot_mode || 'standard'
      },
      visitor: {
        max_per_day: config.visitor?.limits?.profiles_per_run || 15,
        schedule_time: `${String(config.scheduling?.daily_start_hour || 14).padStart(2, '0')}:00`,
        auto_run_enabled: false, // TODO: Store in database or Redis
        mode: 'visit'
      },
      global: {
        daily_start_hour: config.scheduling?.daily_start_hour || 7,
        timezone: config.scheduling?.timezone || 'Europe/Paris',
        working_days: config.scheduling?.working_days || [1, 2, 3, 4, 5]
      }
    };

    return NextResponse.json(structuredConfig);

  } catch (error) {
    return NextResponse.json({
      error: 'Failed to load configuration',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
