import { NextResponse } from 'next/server';
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config';

export async function POST(request: Request) {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const formData = await request.formData();
    const apiUrl = getApiUrl();

    const apiResponse = await fetch(`${apiUrl}/auth/upload`, {
      method: 'POST',
      headers: {
        'X-API-Key': getApiKey()!,
      },
      body: formData,
    });

    const data = await apiResponse.json();

    if (!apiResponse.ok) {
      return NextResponse.json({ detail: data.detail || 'API request failed' }, { status: apiResponse.status });
    }

    return NextResponse.json(data, { status: 200 });
  } catch (error) {
    console.error('Auth upload proxy error:', error);
    return NextResponse.json({ detail: 'Internal server error' }, { status: 500 });
  }
}
