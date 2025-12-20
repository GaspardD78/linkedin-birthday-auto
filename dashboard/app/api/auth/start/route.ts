import { NextResponse } from 'next/server';
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config';

export async function POST(request: Request) {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  const body = await request.json();
  const { email, password } = body;

  try {
    const apiUrl = getApiUrl();

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5 min

    let apiResponse;
    try {
      apiResponse = await fetch(`${apiUrl}/auth/start`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-API-Key': getApiKey()!,
        },
        body: JSON.stringify({ email, password }),
        signal: controller.signal,
      });
    } finally {
      clearTimeout(timeoutId);
    }

    const data = await apiResponse.json();

    if (!apiResponse.ok) {
      return NextResponse.json({ detail: data.detail || 'API request failed' }, { status: apiResponse.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
