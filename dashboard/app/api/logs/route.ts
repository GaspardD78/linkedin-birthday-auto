import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    // Tentative de récupération des logs depuis l'API Python
    const response = await fetch(`${apiUrl}/logs`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      console.warn('Failed to fetch logs from bot API:', response.statusText);
      return NextResponse.json({ logs: [] });
    }

    const data = await response.json();

    // Retourner les logs au format attendu
    return NextResponse.json({ logs: data.logs || data || [] });

  } catch (error) {
    console.error('Error fetching logs:', error);
    // Retourner un tableau vide en cas d'erreur pour ne pas casser l'UI
    return NextResponse.json({ logs: [] });
  }
}
