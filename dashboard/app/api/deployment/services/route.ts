import { NextResponse } from 'next/server';
import { getApiUrl, getApiHeaders, validateApiKey } from '@/lib/api-config';

export async function GET() {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const apiUrl = getApiUrl();

    const response = await fetch(`${apiUrl}/deployment/services/status`, {
      method: 'GET',
      headers: getApiHeaders()
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
