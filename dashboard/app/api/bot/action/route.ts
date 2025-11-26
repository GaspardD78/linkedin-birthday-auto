import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, job_type, dry_run, process_late, limit } = body;

    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    let endpoint = '';
    let payload: any = {};

    if (action === 'start' && job_type === 'birthday') {
      endpoint = '/trigger';
      payload = {
        job_type: 'birthday',
        bot_mode: 'standard',
        dry_run: dry_run ?? true,
        max_days_late: process_late ? 10 : 0
      };
    } else if (action === 'start' && job_type === 'visit') {
      endpoint = '/trigger';
      payload = {
        job_type: 'visit',
        dry_run: dry_run ?? true,
        limit: limit ?? 10
      };
    } else if (action === 'stop') {
      // TODO: Implémenter l'arrêt du bot
      return NextResponse.json({ message: "Stop action not yet implemented" }, { status: 501 });
    } else {
      return NextResponse.json({ error: "Invalid action or job_type" }, { status: 400 });
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

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Bot Action Error:', error);
    return NextResponse.json({ error: 'Internal Server Error' }, { status: 500 });
  }
}
