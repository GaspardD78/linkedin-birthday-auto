import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    let endpoint = '';
    let payload = {};

    if (action === 'start') {
      endpoint = '/trigger';
      payload = {
        bot_mode: 'standard',
        dry_run: false
      };
    } else if (action === 'stop') {
        // Note: L'arrêt n'est pas encore implémenté dans src/api/app.py
        // Pour l'instant on ne fait rien ou on implémente une logique custom
        return NextResponse.json({ message: "Stop not yet implemented via API" }, { status: 501 });
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
