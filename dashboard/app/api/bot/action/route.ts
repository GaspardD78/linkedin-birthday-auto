import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { action, job_type, dry_run, process_late, limit } = body;

    console.log('📡 [PROXY] Requête reçue du dashboard:', { action, job_type, dry_run, process_late, limit });

    // URL interne Docker (CRITIQUE: ne jamais utiliser localhost)
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY || 'internal_secret_key';

    let endpoint = '';
    let payload: any = {};

    // Routage vers les endpoints spécifiques
    if (action === 'start' && job_type === 'birthday') {
      endpoint = '/start-birthday-bot';
      payload = {
        dry_run: dry_run ?? true,
        process_late: process_late ?? false,
        max_days_late: body.max_days_late ?? 10
      };
      console.log('🎂 [PROXY] Appel Birthday Bot:', `${apiUrl}${endpoint}`, payload);
    } else if (action === 'start' && job_type === 'visit') {
      endpoint = '/start-visitor-bot';
      payload = {
        dry_run: dry_run ?? true,
        limit: limit ?? 10
      };
      console.log('🔍 [PROXY] Appel Visitor Bot:', `${apiUrl}${endpoint}`, payload);
    } else if (action === 'stop') {
      // Utiliser le endpoint granulaire /bot/stop au lieu de /stop
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

    const data = await response.json();
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
