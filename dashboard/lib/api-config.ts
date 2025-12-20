/**
 * API Configuration Utils
 * Centralized API key validation and URL management
 */

import { NextResponse } from 'next/server';

/**
 * Get the backend API URL
 * @returns API URL (defaults to http://api:8000 for Docker environment)
 */
export function getApiUrl(): string {
  return process.env.BOT_API_URL || 'http://api:8000';
}

/**
 * Get and validate the API key
 * @returns API key or null if not configured
 */
export function getApiKey(): string | null {
  return process.env.BOT_API_KEY || null;
}

/**
 * Validate that the API key is configured
 * Returns an error response if the key is missing
 * @returns NextResponse with error or null if valid
 */
export function validateApiKey(): NextResponse | null {
  const apiKey = getApiKey();

  if (!apiKey) {
    return NextResponse.json({
      error: 'Server configuration error',
      detail: 'BOT_API_KEY is required but not configured. Please set the environment variable.'
    }, { status: 500 });
  }

  return null;
}

/**
 * Get API headers with authentication
 * @returns Headers object with API key
 */
export function getApiHeaders(): Record<string, string> {
  const apiKey = getApiKey();

  return {
    'Content-Type': 'application/json',
    'X-API-Key': apiKey || ''
  };
}
