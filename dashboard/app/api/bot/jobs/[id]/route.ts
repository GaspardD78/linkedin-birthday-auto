import { NextResponse } from 'next/server';

export async function GET(
  request: Request,
  { params }: { params: { id: string } }
) {
  const job_id = params.id;
  const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
  const apiKey = process.env.BOT_API_KEY;

  if (!apiKey) {
    return NextResponse.json({ error: 'Config error' }, { status: 500 });
  }

  try {
    const response = await fetch(`${apiUrl}/bot/jobs/${job_id}`, {
      headers: {
        'X-API-Key': apiKey
      }
    });

    if (!response.ok) {
      return NextResponse.json({ error: 'Job not found or error' }, { status: response.status });
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: 'Internal Error' }, { status: 500 });
  }
}
