import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

async function handleProxy(request: NextRequest, { params }: { params: { path: string[] } }) {
  try {
    const { path } = params;
    const pathString = path.join('/');

    // URL interne Docker (CRITIQUE: ne jamais utiliser localhost)
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/automation/${pathString}`;

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
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}
