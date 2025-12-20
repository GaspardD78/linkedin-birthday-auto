import { NextResponse } from 'next/server';

export const dynamic = 'force-dynamic';

/**
 * Route Handler CRM Stats - Proxy vers Backend FastAPI
 * Architecture RPi4: Timeout 3s, Zero-Crash Policy, Data Shaping
 * Backend Endpoint: GET /crm/stats
 */
export async function GET() {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    // Timeout de 3s pour libérer le worker Node.js (RPi4 constraint)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    // Appel vers le namespace CRM correct
    const response = await fetch(`${apiUrl}/crm/stats`, {
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
      // Zero-Crash Policy: Retourner structure valide avec stats à zéro
      return NextResponse.json({
        total_contacts: 0,
        total_messages_sent: 0,
        contacts_this_month: 0,
        messages_this_month: 0,
        avg_messages_per_contact: 0.0,
        top_contacted: []
      });
    }

    const data = await response.json();

    // Data Shaping: Retourner uniquement les champs requis (économie bande passante)
    // Le Backend retourne CRMStats conforme au modèle Pydantic
    return NextResponse.json({
      total_contacts: data.total_contacts || 0,
      total_messages_sent: data.total_messages_sent || 0,
      contacts_this_month: data.contacts_this_month || 0,
      messages_this_month: data.messages_this_month || 0,
      avg_messages_per_contact: data.avg_messages_per_contact || 0.0,
      top_contacted: (data.top_contacted || []).slice(0, 5) // Limiter à top 5 (optimisation)
    });

  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
    } else {
    }

    // Zero-Crash Policy: Structure par défaut au lieu d'erreur 500
    return NextResponse.json({
      total_contacts: 0,
      total_messages_sent: 0,
      contacts_this_month: 0,
      messages_this_month: 0,
      avg_messages_per_contact: 0.0,
      top_contacted: []
    });
  }
}
