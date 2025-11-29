import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);
    const service = searchParams.get('service') || 'worker';
    const limit = searchParams.get('limit') || '50';

    const BOT_API_URL = process.env.BOT_API_URL || 'http://api:8000';
    const API_KEY = process.env.BOT_API_KEY || '';

    console.log(`📋 [LOGS API] Proxying log request to Python API: ${BOT_API_URL}/logs?service=${service}&limit=${limit}`);

    try {
      const response = await fetch(`${BOT_API_URL}/logs?service=${service}&limit=${limit}`, {
        headers: {
          'X-API-Key': API_KEY,
          'Accept': 'application/json'
        },
        cache: 'no-store'
      });

      if (!response.ok) {
        console.error(`❌ [LOGS API] Python API error: ${response.status} ${response.statusText}`);
        return NextResponse.json({
            logs: [`[ERROR] Impossible de récupérer les logs depuis l'API Python (${response.status})`]
        });
      }

      const data = await response.json();
      return NextResponse.json(data);

    } catch (fetchError) {
      console.error('❌ [LOGS API] Connection error:', fetchError);
      return NextResponse.json({
        logs: [
          `[ERROR] Erreur de connexion à l'API Python: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}`,
          "[SYSTEM] Vérifiez que le container 'api' est en cours d'exécution."
        ]
      });
    }

  } catch (error) {
    console.error('❌ [LOGS API] Internal error:', error);
    return NextResponse.json({
      logs: [
        `[ERROR] Internal Dashboard Error: ${error instanceof Error ? error.message : String(error)}`
      ]
    });
  }
}
