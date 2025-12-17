import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * Route Handler CRM Activity Timeline - Proxy vers Backend FastAPI
 * Architecture RPi4: Timeout 3s, Zero-Crash Policy, Data Shaping agressif
 * Backend Endpoint: GET /crm/timeline
 *
 * Transformation: /crm/timeline (events: messages + visits) → format simplifié pour widgets
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);

    // Mapping des paramètres vers le contrat CRM Backend
    const days = searchParams.get('days') || '90';
    const contact_name = searchParams.get('contact_name') || '';
    const limit = searchParams.get('limit') || '100'; // Limite client-side

    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    // Construction de l'URL avec namespace CRM
    const queryParams = new URLSearchParams({ days });
    if (contact_name) queryParams.append('contact_name', contact_name);

    // Timeout de 3s pour libérer le worker Node.js (RPi4 constraint)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`${apiUrl}/crm/timeline?${queryParams.toString()}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': apiKey || ''
      },
      cache: 'no-store',
      signal: controller.signal
    });

    clearTimeout(timeoutId);

    if (!response.ok) {
      console.error(`[CRM Activity] Backend returned ${response.status}: ${response.statusText}`);
      // Zero-Crash Policy: Retourner structure valide vide
      return NextResponse.json({
        events: [],
        total: 0,
        days: parseInt(days)
      });
    }

    const data = await response.json();

    // Data Shaping: Optimisation pour RPi4 (limiter la taille des données)
    const events = (data.events || [])
      .slice(0, parseInt(limit)) // Limiter le nombre d'événements
      .map((event: any) => ({
        type: event.type,
        id: event.id,
        contact_name: event.contact_name,
        // Tronquer le détail pour réduire la payload (max 80 chars)
        detail: event.detail ?
          (event.detail.length > 80 ? event.detail.substring(0, 77) + '...' : event.detail) :
          '',
        event_date: event.event_date,
        // Champs conditionnels selon le type
        ...(event.type === 'message' && { is_late: event.is_late || false }),
        ...(event.type === 'visit' && { success: event.success || false })
      }));

    return NextResponse.json({
      events,
      total: Math.min(data.total || 0, parseInt(limit)),
      days: parseInt(days)
    });

  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error('[CRM Activity] Timeout 3s exceeded (RPi4 protection)');
    } else {
      console.error('[CRM Activity] Unexpected error:', error);
    }

    // Zero-Crash Policy: Structure par défaut
    return NextResponse.json({
      events: [],
      total: 0,
      days: 90
    });
  }
}
