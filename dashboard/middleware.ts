import { NextRequest, NextResponse } from "next/server";
import { verifySession } from "@/lib/auth";

export async function middleware(request: NextRequest) {
  // Get session cookie
  const session = request.cookies.get("session")?.value;

  // Verify session
  const payload = session ? await verifySession(session) : null;

  // Protected routes logic
  if (!payload) {
    const loginUrl = new URL("/login", request.url);
    // Redirect to login if trying to access protected route
    return NextResponse.redirect(loginUrl);
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - api (API routes are handled separately)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     * - login (login page)
     */
    "/((?!api|_next/static|_next/image|favicon.ico|login).*)",

    /*
     * Match API routes, but EXCLUDE:
     * - auth/* (login, logout, etc.)
     * - system/* (health checks, etc.)
     */
    "/api/((?!auth|system).*)",
  ],
};
