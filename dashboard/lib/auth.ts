import { SignJWT, jwtVerify } from "jose";

const SECRET_KEY = process.env.JWT_SECRET || "default_secret_key_change_me_in_prod";
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

// Default credentials as requested
export const DEFAULT_USER = process.env.DASHBOARD_USER || "gaspard";
export const DEFAULT_PASSWORD = process.env.DASHBOARD_PASSWORD || "osiris";
