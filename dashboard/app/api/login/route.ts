import { NextResponse } from 'next/server';
import { SignJWT } from 'jose';

// We use the dashboard password as the JWT secret as requested for simplicity.
async function getJwtSecretKey() {
  const secret = process.env.DASHBOARD_PASSWORD;
  if (!secret || secret.length < 32) {
    throw new Error('DASHBOARD_PASSWORD environment variable must be set and be at least 32 characters long');
  }
  return new TextEncoder().encode(secret);
}

export async function POST(req: Request) {
  try {
    const { password } = await req.json();
    const dashboardPassword = process.env.DASHBOARD_PASSWORD;

    if (!dashboardPassword) {
      console.error('DASHBOARD_PASSWORD is not set on the server.');
      return new NextResponse(JSON.stringify({ message: 'Internal Server Error' }), { status: 500 });
    }

    if (password === dashboardPassword) {
      // Password is correct, create a JWT
      const secretKey = await getJwtSecretKey();
      const token = await new SignJWT({ sub: 'dashboard-user' }) // 'sub' (subject) is a standard claim
        .setProtectedHeader({ alg: 'HS256' })
        .setIssuedAt()
        .setExpirationTime('7d')
        .sign(secretKey);

      // Set the token in a secure, HttpOnly cookie
      const response = new NextResponse(JSON.stringify({ success: true }), { status: 200 });
      response.cookies.set({
        name: 'auth_token',
        value: token,
        httpOnly: true,
        secure: process.env.NODE_ENV === 'production',
        sameSite: 'strict',
        path: '/',
        maxAge: 60 * 60 * 24 * 7, // 7 days in seconds
      });

      return response;
    } else {
      // Password is incorrect
      return new NextResponse(JSON.stringify({ message: 'Invalid credentials' }), { status: 401 });
    }
  } catch (error) {
    console.error('Login API error:', error);
    return new NextResponse(JSON.stringify({ message: 'Internal Server Error' }), { status: 500 });
  }
}
