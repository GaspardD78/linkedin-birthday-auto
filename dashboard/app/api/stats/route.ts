import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY;

    // Tentative de récupération des stats depuis l'API Python
    const response = await fetch(`${apiUrl}/stats`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      console.error('Failed to fetch stats from bot API:', response.statusText);
      // Retourner une erreur explicite au lieu de valeurs par défaut silencieuses
      return NextResponse.json(
        {
          error: 'Bot API unreachable',
          detail: `API returned ${response.status}: ${response.statusText}`
        },
        { status: 503 } // Service Unavailable
      );
    }

    const data = await response.json();

    // Retourner les stats au format attendu
    return NextResponse.json({
      wishes_sent_total: data.wishes_sent_total || 0,
      wishes_sent_today: data.wishes_sent_today || 0,
      profiles_visited_total: data.profiles_visited_total || 0,
      profiles_visited_today: data.profiles_visited_today || 0
    });

  } catch (error) {
    console.error('Error fetching stats:', error);
    // Retourner une erreur 500 pour permettre au frontend de détecter le problème
    return NextResponse.json(
      {
        error: 'Internal server error',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
