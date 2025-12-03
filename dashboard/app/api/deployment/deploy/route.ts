import { NextResponse } from 'next/server';
import { getApiUrl, getApiHeaders, validateApiKey } from '@/lib/api-config';

export async function POST(request: Request) {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const body = await request.json();
    const { action, service } = body;

    if (!action) {
      return NextResponse.json({ error: "Missing 'action' parameter" }, { status: 400 });
    }

    const apiUrl = getApiUrl();

    console.log('[DEPLOYMENT] Deploy action:', action, service);

    const response = await fetch(`${apiUrl}/deployment/deploy`, {
      method: 'POST',
      headers: getApiHeaders(),
      body: JSON.stringify({ action, service })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[DEPLOYMENT] Deploy error:', response.status, errorText);
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    const data = await response.json();
    console.log('[DEPLOYMENT] Deploy result:', data);
    return NextResponse.json(data);

  } catch (error) {
    console.error('[DEPLOYMENT] Deploy failed:', error);
    return NextResponse.json({
      error: 'Internal Server Error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
