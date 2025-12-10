"use server";

import { signIn } from "@/auth";
import { AuthError } from "next-auth";

/**
 * Action serveur pour l'authentification par credentials (username/password)
 */
export async function authenticateWithCredentials(
  username: string,
  password: string
) {
  try {
    await signIn("credentials", {
      username,
      password,
      redirect: false,
    });
    return { success: true };
  } catch (error) {
    if (error instanceof AuthError) {
      switch (error.type) {
        case "CredentialsSignin":
          return { success: false, error: "Identifiants invalides" };
        default:
          return { success: false, error: "Une erreur est survenue" };
      }
    }
    throw error;
  }
}

/**
 * Action serveur pour l'authentification Google OAuth
 */
export async function authenticateWithGoogle() {
  try {
    await signIn("google", {
      redirectTo: "/",
    });
  } catch (error) {
    if (error instanceof AuthError) {
      return { success: false, error: "Erreur d'authentification Google" };
    }
    throw error;
  }
}
