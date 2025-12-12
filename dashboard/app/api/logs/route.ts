
import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '100';
    const service = searchParams.get('service') || 'worker';

    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({ error: 'Config Error: BOT_API_KEY missing' }, { status: 500 });
    }

    const response = await fetch(`${apiUrl}/logs?limit=${limit}&service=${service}`, {
        headers: {
            'X-API-Key': apiKey
        },
        cache: 'no-store'
    });

    if (!response.ok) {
        return NextResponse.json(
            { error: 'Logs API Error', detail: response.statusText },
            { status: response.status }
        );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json(
        { error: 'Internal Error', detail: String(error) },
        { status: 500 }
    );
  }
}
