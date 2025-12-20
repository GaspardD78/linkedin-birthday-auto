import { NextResponse, NextRequest } from 'next/server';

export const dynamic = 'force-dynamic';

export async function POST(request: NextRequest) {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const targetUrl = `${apiUrl}/sourcing/export/csv`;

    const body = await request.text();

    const response = await fetch(targetUrl, {
      method: 'POST',
      headers: {
        'X-API-Key': apiKey,
        'Content-Type': 'application/json',
        'Accept': 'text/csv',
      },
      body: body,
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({
        error: 'Export failed',
        detail: errorText
      }, { status: response.status });
    }

    // Return CSV file
    const csvContent = await response.text();
    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=sourcing_export.csv'
      }
    });

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}

export async function GET(request: NextRequest) {
  try {
    const apiUrl = process.env.BOT_API_URL || 'http://api:8000';
    const apiKey = process.env.BOT_API_KEY;

    if (!apiKey) {
      return NextResponse.json({
        error: 'Server configuration error',
        detail: 'BOT_API_KEY is required but not configured'
      }, { status: 500 });
    }

    const searchParams = request.nextUrl.searchParams.toString();
    const targetUrl = `${apiUrl}/sourcing/export/csv${searchParams ? `?${searchParams}` : ''}`;

    const response = await fetch(targetUrl, {
      method: 'GET',
      headers: {
        'X-API-Key': apiKey,
        'Accept': 'text/csv',
      },
      cache: 'no-store',
    });

    if (!response.ok) {
      const errorText = await response.text();
      return NextResponse.json({
        error: 'Export failed',
        detail: errorText
      }, { status: response.status });
    }

    const csvContent = await response.text();
    return new NextResponse(csvContent, {
      status: 200,
      headers: {
        'Content-Type': 'text/csv; charset=utf-8',
        'Content-Disposition': 'attachment; filename=sourcing_export.csv'
      }
    });

  } catch (error) {
    return NextResponse.json({
      error: 'Internal Proxy Error',
      detail: error instanceof Error ? error.message : String(error)
    }, { status: 500 });
  }
}
