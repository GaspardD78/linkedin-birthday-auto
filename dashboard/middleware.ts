import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';
import { jwtVerify } from 'jose';

// We use the dashboard password as the JWT secret as requested for simplicity.
async function getJwtSecretKey() {
  const secret = process.env.DASHBOARD_PASSWORD;
  if (!secret || secret.length < 32) {
    throw new Error('DASHBOARD_PASSWORD environment variable must be set and be at least 32 characters long');
  }
  return new TextEncoder().encode(secret);
}

export async function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;

  const publicPaths = ['/login', '/api/login'];

  // Allow Next.js internals and public assets to pass through
  if (
    pathname.startsWith('/_next') ||
    pathname.startsWith('/static') ||
    pathname.startsWith('/favicon.ico') ||
    pathname.startsWith('/api/health') // Assuming a public health check endpoint
  ) {
    return NextResponse.next();
  }

  // Check if the route is a public API or page
  if (publicPaths.some(path => pathname.startsWith(path))) {
    return NextResponse.next();
  }

  // For all other routes, check for the auth token
  const token = req.cookies.get('auth_token')?.value;
  const loginUrl = new URL('/login', req.url);

  if (!token) {
    // If no token, redirect to login
    return NextResponse.redirect(loginUrl);
  }

  try {
    const secretKey = await getJwtSecretKey();
    // Verify the JWT
    await jwtVerify(token, secretKey);
    // If verification is successful, allow the request to proceed
    return NextResponse.next();
  } catch (error) {
    // If verification fails, the token is invalid
    console.error('JWT Verification failed:', error);
    const response = NextResponse.redirect(loginUrl);
    // Clear the invalid token from the user's browser
    response.cookies.delete('auth_token');
    return response;
  }
}

export const config = {
  // Match all paths except for static files, image optimization files, and the favicon.
  matcher: '/((?!_next/static|_next/image|favicon.ico).*)',
};
