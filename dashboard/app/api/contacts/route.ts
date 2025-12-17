import { NextResponse } from 'next/server';

/**
 * Route Handler CRM Contacts - Proxy vers Backend FastAPI
 * Architecture RPi4: Timeout 3s, Zero-Crash Policy
 * Backend Endpoint: GET /crm/contacts
 */
export async function GET(request: Request) {
  try {
    const { searchParams } = new URL(request.url);

    // Mapping des paramètres vers le contrat CRM Backend
    const page = searchParams.get('page') || '1';
    const per_page = searchParams.get('per_page') || searchParams.get('limit') || '50';
    const search = searchParams.get('search') || '';
    const sort_by = searchParams.get('sort_by') || searchParams.get('sort') || 'last_message_date';
    const sort_order = searchParams.get('sort_order') || 'desc';
    const min_messages = searchParams.get('min_messages') || '';

    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    // Construction de l'URL avec namespace CRM
    const queryParams = new URLSearchParams({
      page,
      per_page,
      sort_by,
      sort_order
    });
    if (search) queryParams.append('search', search);
    if (min_messages) queryParams.append('min_messages', min_messages);

    // Timeout de 3s pour libérer le worker Node.js (RPi4 constraint)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3000);

    const response = await fetch(`${apiUrl}/crm/contacts?${queryParams.toString()}`, {
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
      const errorText = await response.text();
      console.error(`[CRM Contacts] Backend returned ${response.status}: ${errorText}`);
      // Zero-Crash Policy: Retourner structure valide
      return NextResponse.json({
        contacts: [],
        total: 0,
        page: parseInt(page),
        per_page: parseInt(per_page),
        total_pages: 0
      });
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    if (error instanceof Error && error.name === 'AbortError') {
      console.error('[CRM Contacts] Timeout 3s exceeded (RPi4 protection)');
    } else {
      console.error('[CRM Contacts] Unexpected error:', error);
    }

    // Zero-Crash Policy: Structure par défaut
    return NextResponse.json({
      contacts: [],
      total: 0,
      page: 1,
      per_page: 50,
      total_pages: 0
    });
  }
}
