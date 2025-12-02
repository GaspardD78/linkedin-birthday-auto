import { NextResponse } from 'next/server';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const limit = searchParams.get('limit') || '50';
    const sort = searchParams.get('sort') || 'messages';

    const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';
    const apiKey = process.env.BOT_API_KEY;

    const response = await fetch(`${apiUrl}/contacts?limit=${limit}&sort=${sort}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      cache: 'no-store'
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Contacts API Error:', errorText);
      // Retourner des données par défaut au lieu d'une erreur
      return NextResponse.json({ contacts: [] });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('Contacts API Error:', error);
    // Retourner des données par défaut au lieu d'une erreur
    return NextResponse.json({ contacts: [] });
  }
}
