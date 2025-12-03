import { SignJWT, jwtVerify } from "jose";

const SECRET_KEY = process.env.JWT_SECRET;

if (!SECRET_KEY) {
  throw new Error('❌ [SECURITY] JWT_SECRET environment variable is required but not set! Please configure it in your .env file.');
}

const key = new TextEncoder().encode(SECRET_KEY);

export async function signSession(payload: any) {
  return await new SignJWT(payload)
    .setProtectedHeader({ alg: "HS256" })
    .setIssuedAt()
    .setExpirationTime("24h")
    .sign(key);
}

export async function verifySession(token: string) {
  try {
    const { payload } = await jwtVerify(token, key, {
      algorithms: ["HS256"],
    });
    return payload;
  } catch (error) {
    return null;
  }
}

// Default credentials - MUST be set via environment variables
export const DEFAULT_USER = process.env.DASHBOARD_USER;
export const DEFAULT_PASSWORD = process.env.DASHBOARD_PASSWORD;

if (!DEFAULT_USER || !DEFAULT_PASSWORD) {
  throw new Error('❌ [SECURITY] DASHBOARD_USER and DASHBOARD_PASSWORD environment variables are required but not set! Please configure them in your .env file.');
}
