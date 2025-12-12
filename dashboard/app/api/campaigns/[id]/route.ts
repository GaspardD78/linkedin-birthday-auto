
import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, id: string, pathSuffix: string = '') {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      console.error('[SECURITY] BOT_API_KEY environment variable is not set!');
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/campaigns/${id}${pathSuffix}`;
    console.log(`[PROXY] Forwarding ${request.method} to: ${targetUrl}`);

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

    if (request.method !== 'GET' && request.method !== 'HEAD' && request.method !== 'DELETE') {
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

export async function GET(request: NextRequest, { params }: { params: { id: string } }) {
  return handleProxy(request, params.id, '');
}

export async function DELETE(request: NextRequest, { params }: { params: { id: string } }) {
    return handleProxy(request, params.id, '');
}

export async function POST(request: NextRequest, { params }: { params: { id: string } }) {
    // Check if it is a start action or other action
    const url = new URL(request.url);
    if (url.pathname.endsWith('/start')) {
        return handleProxy(request, params.id, '/start');
    }
    if (url.pathname.endsWith('/stop')) {
        return handleProxy(request, params.id, '/stop');
    }
    return handleProxy(request, params.id, '');
}
