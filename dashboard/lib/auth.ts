import "server-only"; // Garantit que ce code ne s'exécute JAMAIS côté client
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

/**
 * Valide les credentials utilisateur de façon sécurisée (server-only).
 *
 * ⚠️ SÉCURITÉ: Ne jamais exposer DEFAULT_USER/DEFAULT_PASSWORD en exports !
 * Cette fonction est la SEULE API pour vérifier les credentials.
 *
 * @param username - Nom d'utilisateur fourni
 * @param password - Mot de passe fourni
 * @returns true si les credentials sont valides, false sinon
 * @throws Error si les variables d'environnement ne sont pas configurées
 */
export function validateUserCredentials(username: string, password: string): boolean {
  const DEFAULT_USER = process.env.DASHBOARD_USER;
  const DEFAULT_PASSWORD = process.env.DASHBOARD_PASSWORD;

  if (!DEFAULT_USER || !DEFAULT_PASSWORD) {
    throw new Error('❌ [SECURITY] DASHBOARD_USER and DASHBOARD_PASSWORD environment variables are required but not set! Please configure them in your .env file.');
  }

  // Validation avec comparaison stricte
  return username === DEFAULT_USER && password === DEFAULT_PASSWORD;
}
