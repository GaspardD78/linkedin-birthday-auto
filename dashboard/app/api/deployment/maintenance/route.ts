import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action } = body;

    if (!action) {
      return NextResponse.json({ error: "Missing 'action' parameter" }, { status: 400 });
    }

    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    console.log('[DEPLOYMENT] Maintenance action:', action);

    const response = await fetch(`${apiUrl}/deployment/maintenance`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      body: JSON.stringify({ action })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[DEPLOYMENT] Maintenance error:', response.status, errorText);
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    const data = await response.json();
    console.log('[DEPLOYMENT] Maintenance success:', data);
    return NextResponse.json(data);

  } catch (error) {
    console.error('[DEPLOYMENT] Maintenance failed:', error);
    return NextResponse.json({
      error: 'Internal Server Error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
