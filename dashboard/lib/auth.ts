import "server-only"; // Garantit que ce code ne s'exécute JAMAIS côté client
import { SignJWT, jwtVerify } from "jose";
import { compareSync } from "bcryptjs";

interface SessionPayload {
  username: string
  [key: string]: string | number | boolean
}

// Lazy initialization to avoid failing during Next.js build time
// The validation will only occur when these functions are actually called at runtime
function getKey(): Uint8Array {
  const SECRET_KEY = process.env.JWT_SECRET;

  if (!SECRET_KEY) {
    throw new Error('❌ [SECURITY] JWT_SECRET environment variable is required but not set! Please configure it in your .env file.');
  }

  return new TextEncoder().encode(SECRET_KEY);
}

export async function signSession(payload: SessionPayload) {
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
 * ⚠️ SÉCURITÉ: Utilise bcrypt pour comparer les mots de passe de façon sécurisée.
 * DASHBOARD_PASSWORD doit être un hash bcrypt (généré avec scripts/hash_password.js).
 * Si le mot de passe n'est pas hashé (pas de $2a$ ou $2b$), il sera comparé en clair
 * pour rétrocompatibilité, mais un warning sera loggé.
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

  // Vérifier username d'abord (évite timing attack sur password si username invalide)
  if (username !== DEFAULT_USER) {
    return false;
  }

  // Détection si le mot de passe est hashé avec bcrypt
  const isPasswordHashed = DEFAULT_PASSWORD.startsWith('$2a$') || DEFAULT_PASSWORD.startsWith('$2b$');

  if (isPasswordHashed) {
    // Comparaison sécurisée avec bcrypt (constant-time)
    try {
      return compareSync(password, DEFAULT_PASSWORD);
    } catch (error) {
      return false;
    }
  } else {
    // Fallback pour rétrocompatibilité (mot de passe en clair)
    return password === DEFAULT_PASSWORD;
  }
}
