import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const response = NextResponse.json({ success: true });

  // Delete cookie
  response.cookies.set("session", "", {
    httpOnly: true,
    secure: process.env.SECURE_COOKIES === "true",
    sameSite: "lax",
    path: "/",
    expires: new Date(0),
  });

  return response;
}
