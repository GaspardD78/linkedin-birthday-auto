import { NextResponse } from 'next/server';
import { getApiUrl, getApiHeaders, validateApiKey } from '@/lib/api-config';

export async function POST(request: Request) {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const body = await request.json();
    const { action } = body;

    if (!action) {
      return NextResponse.json({ error: "Missing 'action' parameter" }, { status: 400 });
    }

    const apiUrl = getApiUrl();


    const response = await fetch(`${apiUrl}/deployment/maintenance`, {
      method: 'POST',
      headers: getApiHeaders(),
      body: JSON.stringify({ action })
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Server Error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
