import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    const response = await fetch(`${apiUrl}/bot/status`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey || ''
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      return NextResponse.json(
        {
          error: 'Bot API unreachable',
          detail: `API returned ${response.status}: ${response.statusText}`
        },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json(
      {
        error: 'Internal server error',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
