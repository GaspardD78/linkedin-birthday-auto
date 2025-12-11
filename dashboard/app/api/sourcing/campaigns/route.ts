import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

// GET /api/sourcing/campaigns - List campaigns
export async function GET(request: NextRequest) {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const searchParams = request.nextUrl.searchParams.toString();
    const targetUrl = `${apiUrl}/sourcing/campaigns${searchParams ? `?${searchParams}` : ''}`;
    console.log(`[PROXY] Forwarding GET to: ${targetUrl}`);

    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey,
        'Accept': 'application/json',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({
        error: 'Backend API Error',
        detail: errorText
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('[PROXY] Campaigns List Error:', error);
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

// POST /api/sourcing/campaigns - Create campaign
export async function POST(request: NextRequest) {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const body = await request.json();
    const targetUrl = `${apiUrl}/sourcing/campaigns`;
    console.log(`[PROXY] Forwarding POST to: ${targetUrl}`);

    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({
        error: 'Backend API Error',
        detail: errorText
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('[PROXY] Campaign Create Error:', error);
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}
