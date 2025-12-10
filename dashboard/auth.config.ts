import type { NextAuthConfig } from "next-auth";
import Google from "next-auth/providers/google";
import Credentials from "next-auth/providers/credentials";
import { validateUserCredentials } from "@/lib/auth";

/**
 * Configuration NextAuth avec support de :
 * 1. Google OAuth (n'importe quel compte Google)
 * 2. Credentials (username/password existant)
 */
export const authConfig: NextAuthConfig = {
  providers: [
    // Google OAuth Provider
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET,
      authorization: {
        params: {
          prompt: "consent",
          access_type: "offline",
          response_type: "code"
        }
      }
    }),

    // Credentials Provider (système existant username/password)
    Credentials({
      name: "Credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" }
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) {
          return null;
        }

        try {
          const isValid = validateUserCredentials(
            credentials.username as string,
            credentials.password as string
          );

          if (isValid) {
            return {
              id: "dashboard-user",
              name: credentials.username as string,
              email: null,
            };
          }
          return null;
        } catch (error) {
          console.error("❌ [AUTH] Credentials validation error:", error);
          return null;
        }
      }
    })
  ],

  pages: {
    signIn: "/login",
  },

  callbacks: {
    authorized({ auth, request: { nextUrl } }) {
      const isLoggedIn = !!auth?.user;
      const isOnLoginPage = nextUrl.pathname === "/login";

      if (isLoggedIn && isOnLoginPage) {
        return Response.redirect(new URL("/", nextUrl));
      }

      if (!isLoggedIn && !isOnLoginPage) {
        return false;
      }

      return true;
    },

    async jwt({ token, user, account }) {
      // Lors de la première connexion, ajouter l'info du provider
      if (account && user) {
        token.provider = account.provider;
        token.userId = user.id;
      }
      return token;
    },

    async session({ session, token }) {
      // Ajouter les infos du token à la session
      if (token) {
        session.user.provider = token.provider as string;
        session.user.id = token.userId as string;
      }
      return session;
    },
  },

  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 heures (comme l'ancien système)
  },

  secret: process.env.AUTH_SECRET,
};
