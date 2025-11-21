#!/usr/bin/env python3
"""
Script Simplifié pour Générer auth_state.json
==============================================

Ce script lance un navigateur Chromium, vous permet de vous connecter
manuellement à LinkedIn (avec 2FA si activé), puis sauvegarde l'état
d'authentification dans auth_state.json.

Usage:
    python3 generate_auth_simple.py

Le fichier auth_state.json sera créé dans le dossier courant.
Utilisez ce fichier pour configurer le bot sur votre Raspberry Pi.
"""

import os
from playwright.sync_api import sync_playwright

AUTH_FILE_PATH = "auth_state.json"

def main():
    print("\n" + "="*80)
    print("📱 GÉNÉRATION DE auth_state.json POUR LINKEDIN")
    print("="*80)
    print("\n✨ Ce script va :")
    print("  1. Ouvrir un navigateur Chromium")
    print("  2. Vous rediriger vers la page de connexion LinkedIn")
    print("  3. Attendre que vous vous connectiez (email, mot de passe, 2FA)")
    print("  4. Sauvegarder votre session dans auth_state.json")
    print("\n⚠️  IMPORTANT :")
    print("  - NE FERMEZ PAS le navigateur vous-même")
    print("  - Une fois connecté à LinkedIn, revenez ici et appuyez sur Entrée")
    print("\n" + "="*80 + "\n")

    input("Appuyez sur Entrée pour commencer...")

    with sync_playwright() as p:
        # Lancer le navigateur en mode visible (headless=False)
        print("\n🌐 Ouverture du navigateur Chromium...")
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        # Aller sur la page de connexion LinkedIn
        print("🔗 Navigation vers la page de connexion LinkedIn...")
        page.goto("https://www.linkedin.com/login")

        print("\n" + "="*80)
        print("✋ VOTRE TOUR !")
        print("="*80)
        print("\nDans le navigateur qui vient de s'ouvrir :")
        print("  1. Entrez votre email LinkedIn")
        print("  2. Entrez votre mot de passe")
        print("  3. Si vous avez le 2FA, entrez le code demandé")
        print("  4. Attendez d'être sur votre page d'accueil LinkedIn")
        print("  5. Revenez ici et appuyez sur Entrée")
        print("\n⚠️  NE FERMEZ PAS le navigateur, il se fermera automatiquement.\n")
        print("="*80 + "\n")

        input("✅ Je suis connecté à LinkedIn, appuyez sur Entrée pour continuer...")

        # Sauvegarder l'état d'authentification
        print("\n💾 Sauvegarde de l'état d'authentification...")
        context.storage_state(path=AUTH_FILE_PATH)

        print(f"✅ Fichier '{AUTH_FILE_PATH}' créé avec succès !")

        # Fermer le navigateur
        print("🚪 Fermeture du navigateur...")
        browser.close()

        print("\n" + "="*80)
        print("🎉 TERMINÉ !")
        print("="*80)
        print(f"\nLe fichier '{AUTH_FILE_PATH}' a été créé dans le dossier :")
        print(f"  {os.path.abspath(AUTH_FILE_PATH)}")
        print("\n📋 Prochaines étapes :")
        print("  1. Copiez ce fichier sur votre Raspberry Pi :")
        print(f"     scp {AUTH_FILE_PATH} pi@raspberrypi.local:~/linkedin-birthday-auto/")
        print("  2. Le bot utilisera automatiquement ce fichier pour se connecter")
        print("  3. Plus besoin de saisir le code 2FA à chaque exécution !")
        print("\n💡 Astuce : Ce fichier est valide pendant plusieurs semaines.")
        print("   Si LinkedIn vous déconnecte, relancez simplement ce script.")
        print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interruption par l'utilisateur. Abandon.")
    except Exception as e:
        print(f"\n\n❌ Erreur : {e}")
        print("\nVérifiez que Playwright est installé :")
        print("  pip install playwright")
        print("  playwright install chromium")
