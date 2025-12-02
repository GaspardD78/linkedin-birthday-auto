import { NextRequest, NextResponse } from "next/server";
import { signSession, DEFAULT_USER, DEFAULT_PASSWORD } from "@/lib/auth";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { username, password } = body;

    if (username === DEFAULT_USER && password === DEFAULT_PASSWORD) {
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
    return NextResponse.json(
      { success: false, message: "Erreur serveur" },
      { status: 500 }
    );
  }
}
