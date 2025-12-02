import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  const { email, password } = body;

  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min

    let apiResponse;
    try {
      apiResponse = await fetch(`${apiUrl}/auth/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': process.env.BOT_API_KEY || 'internal_secret_key',
        },
        body: JSON.stringify({ email, password }),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    const data = await apiResponse.json();

    if (!apiResponse.ok) {
      return NextResponse.json({ detail: data.detail || 'API request failed' }, { status: apiResponse.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Auth start proxy error:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
