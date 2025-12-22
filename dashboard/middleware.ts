import { NextRequest, NextResponse } from "next/server";
import { verifySession } from "@/lib/auth";

export async function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl;

  // 1. Define Public Routes
  // These routes do not require authentication
  const isPublicRoute =
    pathname === "/login" ||
    pathname.startsWith("/api/auth") ||
    pathname.startsWith("/api/system");

  if (isPublicRoute) {
    return NextResponse.next();
  }

  // 2. Verify Session for Protected Routes
  const session = request.cookies.get("session")?.value;
  const payload = session ? await verifySession(session) : null;

  // 3. Handle Unauthorized Access
  if (!payload) {
    // API Routes -> Return JSON 401 instead of redirecting
    // This prevents the frontend from trying to parse HTML as JSON
    if (pathname.startsWith("/api/")) {
      return NextResponse.json(
        { error: "Unauthorized" },
        { status: 401 }
      );
    }

    // UI Routes -> Redirect to /login
    // Avoid redirect loops by checking we are not already on login (covered by isPublicRoute, but safety first)
    if (!pathname.startsWith("/login")) {
        const loginUrl = new URL("/login", request.url);
        return NextResponse.redirect(loginUrl);
    }
  }

  return NextResponse.next();
}

export const config = {
  matcher: [
    /*
     * Match all request paths except for the ones starting with:
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico (favicon file)
     */
    "/((?!_next/static|_next/image|favicon.ico).*)",
  ],
};
