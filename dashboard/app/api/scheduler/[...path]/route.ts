/**
 * Next.js API Route for Scheduler
 *
 * Proxies all /api/scheduler/* requests to FastAPI backend.
 * Catch-all route handles: GET, POST, PUT, DELETE
 */

import { NextRequest, NextResponse } from 'next/server';

// Backend API configuration
const API_BASE_URL = process.env.BOT_API_URL || 'http://api:8000';
const API_KEY = process.env.BOT_API_KEY;

/**
 * Proxy request to FastAPI backend with authentication.
 */
async function proxyToBackend(
  method: string,
  path: string,
  body?: any,
  searchParams?: URLSearchParams
): Promise<NextResponse> {
  // Validate API key
  if (!API_KEY) {
    console.error('❌ [SCHEDULER] BOT_API_KEY not configured');
    return NextResponse.json(
      {
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured',
      },
      { status: 500 }
    );
  }

  // Build URL
  const url = new URL(`/scheduler/${path}`, API_BASE_URL);
  if (searchParams) {
    searchParams.forEach((value, key) => {
      url.searchParams.append(key, value);
    });
  }

  console.log(`📡 [SCHEDULER] ${method} ${url.pathname}${url.search}`);

  try {
    // Make request to backend
    const response = await fetch(url.toString(), {
      method,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': API_KEY,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    // Handle 204 No Content (DELETE success)
    if (response.status === 204) {
      return new NextResponse(null, { status: 204 });
    }

    // Parse response robustly
    const text = await response.text();
    let data;

    try {
      data = text ? JSON.parse(text) : {};
    } catch (e) {
      console.error(`❌ [SCHEDULER] Failed to parse backend response: ${text.substring(0, 100)}...`);
      return NextResponse.json(
        {
          error: 'Invalid backend response',
          detail: 'The backend returned a non-JSON response.',
          raw_response: text.substring(0, 200)
        },
        { status: 502 }
      );
    }

    // Log errors
    if (!response.ok) {
      console.error(`❌ [SCHEDULER] Error ${response.status}:`, data);
    }

    // Return response with same status code
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error('❌ [SCHEDULER] Backend request failed:', error);
    return NextResponse.json(
      {
        error: 'Backend request failed',
        detail: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 503 }
    );
  }
}

/**
 * GET handler
 *
 * Routes:
 * - GET /api/scheduler/jobs
 * - GET /api/scheduler/jobs/{id}
 * - GET /api/scheduler/jobs/{id}/history
 * - GET /api/scheduler/health
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const searchParams = request.nextUrl.searchParams;

  return proxyToBackend('GET', path, undefined, searchParams);
}

/**
 * POST handler
 *
 * Routes:
 * - POST /api/scheduler/jobs (create job)
 * - POST /api/scheduler/jobs/{id}/toggle
 * - POST /api/scheduler/jobs/{id}/run
 */
export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');

  let body;
  try {
    const text = await request.text();
    body = text ? JSON.parse(text) : undefined;
  } catch (e) {
    // Body is optional or empty
  }

  console.log(`📝 [SCHEDULER] POST body:`, body);

  return proxyToBackend('POST', path, body);
}

/**
 * PUT handler
 *
 * Routes:
 * - PUT /api/scheduler/jobs/{id} (update job)
 */
export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');
  const body = await request.json();

  console.log(`📝 [SCHEDULER] PUT body:`, body);

  return proxyToBackend('PUT', path, body);
}

/**
 * DELETE handler
 *
 * Routes:
 * - DELETE /api/scheduler/jobs/{id}
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
) {
  const path = params.path.join('/');

  return proxyToBackend('DELETE', path);
}
