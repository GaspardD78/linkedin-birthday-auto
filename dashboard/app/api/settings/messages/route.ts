import { NextResponse } from 'next/server';
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config';

export async function GET() {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const res = await fetch(`${getApiUrl()}/config/messages`, { headers: { 'X-API-Key': getApiKey()! } });
    if (!res.ok) {
        const errorText = await res.text();
        return NextResponse.json({ error: errorText }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) { return NextResponse.json({ error: 'Failed to fetch' }, { status: 500 }); }
}

export async function POST(req: Request) {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const body = await req.json();
    const res = await fetch(`${getApiUrl()}/config/messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': getApiKey()! },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
        const errorText = await res.text();
        return NextResponse.json({ error: errorText }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (e) { return NextResponse.json({ error: 'Failed to fetch' }, { status: 500 }); }
}
