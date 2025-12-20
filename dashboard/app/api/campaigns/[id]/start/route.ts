
import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, id: string, action: string) {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/campaigns/${id}/${action}`;

    const headers: Record<string, string> = {
      'X-API-Key': apiKey,
      'Accept': 'application/json',
      'Content-Type': 'application/json'
    };

    const fetchOptions: RequestInit = {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(await request.json().catch(() => ({})))
    };

    const response = await fetch(targetUrl, fetchOptions);

    if (!response.ok) {
       const errorText = await response.text();
       return NextResponse.json({
         error: 'Backend API Error',
         detail: `API returned ${response.status}`,
         backend_message: errorText
       }, { status: response.status });
    }

    return NextResponse.json(await response.json());

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: String(error)
    }, { status: 500 });
  }
}

export async function POST(request: NextRequest, { params }: { params: { id: string } }) {
  return handleProxy(request, params.id, 'start');
}
