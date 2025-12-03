import { NextResponse } from 'next/server';
import { getApiUrl, getApiKey, validateApiKey } from '@/lib/api-config';

/**
 * GET /api/auth/validate-cookies
 *
 * Validates LinkedIn cookies by checking their expiration dates
 * Returns cookie status and expiration information
 */
export async function GET() {
  // Validate API key is configured
  const validationError = validateApiKey();
  if (validationError) return validationError;

  try {
    const apiUrl = getApiUrl();

    // Call backend to get auth state status
    const response = await fetch(`${apiUrl}/auth/status`, {
      method: 'GET',
      headers: {
        'X-API-Key': getApiKey()!
      }
    });

    if (!response.ok) {
      // If backend doesn't have auth/status endpoint, return default
      return NextResponse.json({
        valid: false,
        error: 'Could not verify cookie status',
        expires_at: null,
        last_updated: null
      });
    }

    const data = await response.json();

    // Backend should return: { auth_available: boolean, cookies_valid: boolean, expires_at: string }
    return NextResponse.json({
      valid: data.cookies_valid ?? data.auth_available ?? false,
      expires_at: data.expires_at || null,
      last_updated: data.last_updated || new Date().toISOString()
    });

  } catch (error) {
    console.error('[AUTH] Failed to validate cookies:', error);

    // Return a safe default instead of erroring
    return NextResponse.json({
      valid: false,
      error: 'Failed to check cookie status',
      expires_at: null,
      last_updated: null
    });
  }
}
