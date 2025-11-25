import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const body = await request.json();
  const { email, password } = body;

  try {
    const apiResponse = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/auth/start`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.BOT_API_KEY || '',
      },
      body: JSON.stringify({ email, password }),
    });

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
