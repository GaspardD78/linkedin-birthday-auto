import { NextRequest, NextResponse } from "next/server";
import { signSession, validateUserCredentials } from "@/lib/auth";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    // Valider les credentials de façon sécurisée (server-only)
    if (validateUserCredentials(username, password)) {
      // Create session
      const token = await signSession({ username });

      // Create response
      const response = NextResponse.json({ success: true });

      // Set cookie
      response.cookies.set("session", token, {
        httpOnly: true,
        secure: process.env.SECURE_COOKIES === "true",
        sameSite: "lax",
        path: "/",
        maxAge: 60 * 60 * 24, // 24 hours
      });

      return response;
    }

    return NextResponse.json(
      { success: false, message: "Identifiants incorrects" },
      { status: 401 }
    );
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Erreur serveur";

    // Return more descriptive error for configuration issues
    if (errorMessage.includes('JWT_SECRET') || errorMessage.includes('DASHBOARD_USER') || errorMessage.includes('DASHBOARD_PASSWORD')) {
      return NextResponse.json(
        {
          success: false,
          message: "Configuration manquante. Veuillez configurer les variables d'environnement (JWT_SECRET, DASHBOARD_USER, DASHBOARD_PASSWORD)."
        },
        { status: 500 }
      );
    }

    return NextResponse.json(
      { success: false, message: "Erreur serveur" },
      { status: 500 }
    );
  }
}
