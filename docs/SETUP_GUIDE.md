## 🔧 Dépannage Hachage Mot de Passe

**Problème : Le setup échoue à l'étape "Configuration Mot de Passe Dashboard"**

Si le hachage échoue, le système tente de basculer sur des méthodes alternatives (htpasswd, openssl). Cependant, la méthode recommandée est l'image Docker sécurisée.

**Solutions :**

1.  **Vérifier l'image Docker :**
    Assurez-vous que l'image de sécurité peut être téléchargée.
    ```bash
    docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard/pi-security-hash:latest
    ```

2.  **Tester le hachage manuellement :**
    Utilisez la fonction de test intégrée à la librairie de sécurité :
    ```bash
    # Sourcer les dépendances (si nécessaire)
    source scripts/lib/common.sh 2>/dev/null || true
    source scripts/lib/security.sh

    # Lancer le test
    test_hash
    ```
    Cela devrait afficher un hash bcrypt valide sans erreur.

3.  **Vérifier le fichier .env :**
    Si le mot de passe semble défini mais ne fonctionne pas, vérifiez qu'il est bien échappé (double `1276`) dans le fichier `.env`.
    ```bash
    grep DASHBOARD_PASSWORD .env
    ```
