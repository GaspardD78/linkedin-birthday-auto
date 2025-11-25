import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    let endpoint = '';
    let payload: any = {};

    if (action === 'visit') {
        endpoint = '/trigger';
        payload = { job_type: 'visit', dry_run: false };
    } else if (action === 'start') {
      endpoint = '/trigger';
      payload = {
        job_type: 'birthday',
        bot_mode: 'standard',
        dry_run: false
      };
    } else {
        return NextResponse.json({ error: "Invalid action" }, { status: 400 });
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
