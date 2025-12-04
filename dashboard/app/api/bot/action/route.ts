import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, job_type, dry_run, process_late, limit } = body;

    console.log('📡 [PROXY] Requête reçue du dashboard:', { action, job_type, dry_run, process_late, limit });

    // URL interne Docker (CRITIQUE: ne jamais utiliser localhost)
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      console.error('❌ [SECURITY] BOT_API_KEY environment variable is not set!');
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    let endpoint = '';
    let payload: any = {};

    // Routage vers les endpoints spécifiques (Architecture V2 - Routes /bot/*)
    if (action === 'start' && job_type === 'birthday') {
      endpoint = '/bot/start/birthday';
      payload = {
        dry_run: dry_run ?? true,
        process_late: process_late ?? false,
        max_days_late: body.max_days_late ?? 10
      };
      console.log('🎂 [PROXY] Appel Birthday Bot:', `${apiUrl}${endpoint}`, payload);
    } else if (action === 'start' && job_type === 'visit') {
      endpoint = '/bot/start/visitor';
      payload = {
        dry_run: dry_run ?? true,
        limit: limit ?? 10
      };
      console.log('🔍 [PROXY] Appel Visitor Bot:', `${apiUrl}${endpoint}`, payload);
    } else if (action === 'stop') {
      endpoint = '/bot/stop';
      payload = {};

      // Ajouter job_type si fourni (pour arrêt par type)
      if (body.job_type) {
        payload.job_type = body.job_type;
      }

      // Ajouter job_id si fourni (pour arrêt par ID spécifique)
      if (body.job_id) {
        payload.job_id = body.job_id;
      }

      console.log('🛑 [PROXY] Appel Stop Bot:', `${apiUrl}${endpoint}`, payload);
    } else {
      console.error('❌ [PROXY] Action invalide:', { action, job_type });
      return NextResponse.json({ error: "Invalid action or job_type" }, { status: 400 });
    }

    console.log('🚀 [PROXY] Envoi vers API Python:', `${apiUrl}${endpoint}`);

    const response = await fetch(`${apiUrl}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey
      },
      body: JSON.stringify(payload)
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ [PROXY] Erreur API:', response.status, errorText);
      return NextResponse.json({ error: errorText }, { status: response.status });
    }

    // Try to parse JSON response, handle potential HTML errors
    const contentType = response.headers.get('content-type');
    let data;

    if (contentType && contentType.includes('application/json')) {
      try {
        data = await response.json();
      } catch (parseError) {
        console.error('❌ [PROXY] Failed to parse JSON despite content-type header');
        return NextResponse.json({
          error: 'Backend returned malformed JSON'
        }, { status: 500 });
      }
    } else {
      // Backend returned non-JSON (probably HTML error page)
      const textResponse = await response.text();
      console.error('❌ [PROXY] Backend returned non-JSON:', textResponse.substring(0, 500));
      return NextResponse.json({
        error: 'Backend returned invalid response (not JSON)',
        detail: textResponse.substring(0, 500)
      }, { status: 500 });
    }

    console.log('✅ [PROXY] Réponse de l\'API:', data);
    return NextResponse.json(data);

  } catch (error) {
    console.error('❌ [PROXY] Erreur fatale:', error);
    return NextResponse.json({
      error: 'Internal Server Error',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
