import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, pathSuffix: string = '') {
  try {
    // URL interne Docker (CRITIQUE: ne jamais utiliser localhost)
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      console.error('[SECURITY] BOT_API_KEY environment variable is not set!');
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/blacklist${pathSuffix}`;
    console.log(`[PROXY] Forwarding ${request.method} to: ${targetUrl}`);

    const headers: Record<string, string> = {
      'X-API-Key': apiKey,
      'Accept': 'application/json',
    };

    // Forward Content-Type if present
    const contentType = request.headers.get('content-type');
    if (contentType) {
      headers['Content-Type'] = contentType;
    }

    const fetchOptions: RequestInit = {
      method: request.method,
      headers: headers,
      cache: 'no-store',
    };

    // Forward body for non-GET/HEAD requests
    if (request.method !== 'GET' && request.method !== 'HEAD') {
      try {
        const body = await request.text();
        if (body) {
          fetchOptions.body = body;
        }
      } catch (e) {
        console.warn('[PROXY] Could not read request body', e);
      }
    }

    const response = await fetch(targetUrl, fetchOptions);

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`[PROXY] Backend error (${response.status}): ${errorText.substring(0, 200)}`);
      return NextResponse.json({
        error: 'Backend API Error',
        detail: `API returned ${response.status}: ${response.statusText}`,
        backend_message: errorText
      }, { status: response.status });
    }

    // Handle response content type
    const responseContentType = response.headers.get('content-type');
    if (responseContentType && responseContentType.includes('application/json')) {
      const data = await response.json();
      return NextResponse.json(data);
    } else {
      const text = await response.text();
      return new NextResponse(text, {
        status: response.status,
        headers: {
          'Content-Type': responseContentType || 'text/plain'
        }
      });
    }

  } catch (error) {
    console.error('[PROXY] Internal Proxy Error:', error);
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  // Get query params for include_inactive
  const searchParams = request.nextUrl.searchParams;
  const includeInactive = searchParams.get('include_inactive');
  const pathSuffix = includeInactive ? `?include_inactive=${includeInactive}` : '';
  return handleProxy(request, pathSuffix);
}

export async function POST(request: NextRequest) {
  return handleProxy(request);
}
