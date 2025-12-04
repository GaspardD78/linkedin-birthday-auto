import { SignJWT, jwtVerify } from "jose";

// Lazy initialization to avoid failing during Next.js build time
// The validation will only occur when these functions are actually called at runtime
function getKey(): Uint8Array {
  const SECRET_KEY = process.env.JWT_SECRET;

  if (!SECRET_KEY) {
    throw new Error('❌ [SECURITY] JWT_SECRET environment variable is required but not set! Please configure it in your .env file.');
  }

  return new TextEncoder().encode(SECRET_KEY);
}

export async function signSession(payload: any) {
  return await new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("24h")
    .sign(getKey());
}

export async function verifySession(token: string) {
  try {
    const { payload } = await jwtVerify(token, getKey(), {
      algorithms: ["HS256"],
    });
    return payload;
  } catch (error) {
    return null;
  }
}

// Default credentials - Lazy evaluation to avoid build-time failures
function getCredentials() {
  const DEFAULT_USER = process.env.DASHBOARD_USER;
  const DEFAULT_PASSWORD = process.env.DASHBOARD_PASSWORD;

  if (!DEFAULT_USER || !DEFAULT_PASSWORD) {
    throw new Error('❌ [SECURITY] DASHBOARD_USER and DASHBOARD_PASSWORD environment variables are required but not set! Please configure them in your .env file.');
  }

  return { DEFAULT_USER, DEFAULT_PASSWORD };
}

// Export constants with fallback for build time, but actual validation happens at runtime
export const DEFAULT_USER = process.env.DASHBOARD_USER || '';
export const DEFAULT_PASSWORD = process.env.DASHBOARD_PASSWORD || '';

// Runtime validation helper
export function validateCredentials() {
  getCredentials(); // This will throw if credentials are missing
}
