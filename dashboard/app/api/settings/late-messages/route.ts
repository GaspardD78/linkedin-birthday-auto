import { NextResponse } from 'next/server';

const API_URL = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
const API_KEY = process.env.BOT_API_KEY || 'internal_secret_key';

export async function GET() {
  try {
    const res = await fetch(`${API_URL}/config/late-messages`, { headers: { 'X-API-Key': API_KEY } });
    if (!res.ok) {
        const errorText = await res.text();
        return NextResponse.json({ error: errorText }, { status: res.status });
    }
    const data = await res.json();
    return NextResponse.json(data);
  } catch (e) { return NextResponse.json({ error: 'Failed to fetch' }, { status: 500 }); }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const res = await fetch(`${API_URL}/config/late-messages`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY },
      body: JSON.stringify(body)
    });
    if (!res.ok) {
        const errorText = await res.text();
        return NextResponse.json({ error: errorText }, { status: res.status });
    }
    return NextResponse.json(await res.json());
  } catch (e) { return NextResponse.json({ error: 'Failed to fetch' }, { status: 500 }); }
}
