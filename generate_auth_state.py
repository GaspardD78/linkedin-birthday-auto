import os
import base64
from playwright.sync_api import sync_playwright

AUTH_FILE_PATH = "auth_state.json"

def generate_auth_state():
    """
    Lance un navigateur pour que l'utilisateur se connecte manuellement à LinkedIn.
    Après connexion, sauvegarde l'état d'authentification (cookies, etc.)
    et affiche les instructions pour créer un secret GitHub.
    """
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()

        print("\n" + "="*80)
        print("--- INSTRUCTIONS ---")
        print("1. Une fenêtre de navigateur va s'ouvrir sur la page de connexion de LinkedIn.")
        print("2. Veuillez vous connecter à votre compte (avec email, mot de passe et code 2FA).")
        print("3. Une fois connecté(e) et sur la page principale de LinkedIn, ne fermez PAS le navigateur.")
        print("4. Revenez à ce terminal et appuyez sur 'Entrée' pour continuer.")
        print("="*80 + "\n")

        page.goto("https://www.linkedin.com/login")

        input("Appuyez sur 'Entrée' une fois que vous êtes connecté(e) à LinkedIn dans le navigateur...")

        # Sauvegarde de l'état d'authentification
        page.context.storage_state(path=AUTH_FILE_PATH)
        print(f"L'état d'authentification a été sauvegardé dans '{AUTH_FILE_PATH}'.")

        browser.close()

        # Encodage du fichier en Base64
        try:
            with open(AUTH_FILE_PATH, "rb") as f:
                auth_state_bytes = f.read()

            auth_state_base64 = base64.b64encode(auth_state_bytes).decode('utf-8')

            print("\n" + "="*80)
            print("--- ACTION REQUISE ---")
            print("Pour utiliser cette authentification dans votre script, vous devez créer un secret sur GitHub :")
            print("1. Allez dans les 'Settings' de votre dépôt GitHub.")
            print("2. Naviguez vers 'Secrets and variables' > 'Actions'.")
            print("3. Cliquez sur 'New repository secret'.")
            print("4. Nommez le secret : LINKEDIN_AUTH_STATE")
            print("5. Copiez la longue chaîne de caractères ci-dessous et collez-la comme valeur du secret.")
            print("="*80 + "\n")
            print("CONTENU DU SECRET À COPIER :\n")
            print(auth_state_base64)
            print("\n" + "="*80)

        except Exception as e:
            print(f"\nUne erreur est survenue lors de l'encodage du fichier : {e}")
        finally:
            # Nettoyage du fichier local pour la sécurité
            if os.path.exists(AUTH_FILE_PATH):
                os.remove(AUTH_FILE_PATH)
                print(f"Le fichier local '{AUTH_FILE_PATH}' a été supprimé pour votre sécurité.")


if __name__ == "__main__":
    print("Ce script va vous aider à vous authentifier à LinkedIn de manière sécurisée.")
    print("Il ne sauvegarde ni votre mot de passe ni vos informations personnelles.")
    generate_auth_state()
