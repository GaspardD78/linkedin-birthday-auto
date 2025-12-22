import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, job_type, dry_run, process_late, limit } = body;


    // URL interne Docker (CRITIQUE: ne jamais utiliser localhost)
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    let endpoint = '';
    let payload: any = {};

    // Routage unifié vers /bot/action (Architecture V3)
    endpoint = '/bot/action';

    // Pass the body directly, ensuring it matches BotActionRequest structure
    // api.ts sends: { action, job_type, config: {...} }
    // If request body is flat (legacy), adapt it.

    if (body.config) {
        payload = body; // Already V3 format
    } else {
        // Adapt Legacy flat format to V3 BotActionRequest
        payload = {
            action: action,
            job_type: job_type,
            config: {}
        };

        if (job_type === 'birthday') {
            payload.config = {
                dry_run: dry_run ?? true,
                process_late: process_late ?? false,
                max_days_late: body.max_days_late ?? 10
            };
        } else if (job_type === 'visit') {
            payload.config = {
                dry_run: dry_run ?? true,
                limit: limit ?? 10
            };
        } else if (action === 'stop') {
             // For stop, job_type is optional in legacy /stop but required in /action
             // If missing, use 'all' or handle on backend
             payload.job_type = body.job_type || 'all';
             // We might want to use specific endpoint for stop if V3 /action is strict
             if (!body.job_type && !body.job_id) {
                 // Emergency stop
                 endpoint = '/bot/stop';
                 payload = {};
             } else {
                 endpoint = '/bot/stop'; // Stick to /stop for now for safety as per my Python implementation of /action
                 payload = { job_type: body.job_type, job_id: body.job_id };
             }
        }
    }


    const response = await fetch(`${apiUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    // Try to parse JSON response, handle potential HTML errors
    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch (parseError) {
        return NextResponse.json({
          error: 'Backend returned malformed JSON'
        }, { status: 500 });
      }
    } else {
      // Backend returned non-JSON (probably HTML error page)
      const textResponse = await response.text();
      return NextResponse.json({
        error: 'Backend returned invalid response (not JSON)',
        detail: textResponse.substring(0, 500)
      }, { status: 500 });
    }

    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Server Error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
