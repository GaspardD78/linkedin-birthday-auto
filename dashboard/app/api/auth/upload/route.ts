import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const formData = await request.formData();
    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';

    const apiResponse = await fetch(`${apiUrl}/auth/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': process.env.BOT_API_KEY || 'internal_secret_key',
      },
      body: formData,
    });

    const data = await apiResponse.json();

    if (!apiResponse.ok) {
      return NextResponse.json({ detail: data.detail || 'API request failed' }, { status: apiResponse.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Auth upload proxy error:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
