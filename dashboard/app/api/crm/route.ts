import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, pathSuffix: string = '') {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/crm${pathSuffix}`;

    const headers: Record<string, string> = {
      'X-API-Key': apiKey,
      'Accept': 'application/json',
    };

    const contentType = request.headers.get('content-type');
    if (contentType) {
      headers['Content-Type'] = contentType;
    }

    const fetchOptions: RequestInit = {
      method: request.method,
      headers: headers,
      cache: 'no-store',
    };

    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        const body = await request.text();
        if (body) {
          fetchOptions.body = body;
        }
      } catch (e) {
      }
    }

    const response = await fetch(targetUrl, fetchOptions);

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({
        error: 'Backend API Error',
        detail: `API returned ${response.status}: ${response.statusText}`,
        backend_message: errorText
      }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams.toString();
  const pathSuffix = `/contacts${searchParams ? `?${searchParams}` : ''}`;
  return handleProxy(request, pathSuffix);
}
