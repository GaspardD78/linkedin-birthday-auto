import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET() {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    // Tentative de récupération des stats depuis l'API Python
    const response = await fetch(`${apiUrl}/stats`, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      console.warn('Failed to fetch stats from bot API:', response.statusText);
      // Retourner des valeurs par défaut si l'API ne répond pas
      return NextResponse.json({
        wishes_sent_total: 0,
        wishes_sent_today: 0,
        profiles_visited_total: 0,
        profiles_visited_today: 0
      });
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
    // Retourner des valeurs par défaut en cas d'erreur
    return NextResponse.json({
      wishes_sent_total: 0,
      wishes_sent_today: 0,
      profiles_visited_total: 0,
      profiles_visited_today: 0
    });
  }
}
