# 🔧 Guide de Résolution : Authentification rclone dans Docker

## 🚨 Problème Rencontré

Vous voyez ce message :
```
2025/12/10 11:28:51 ERROR : Failed to open browser automatically (exec: "xdg-open": executable file not found in $PATH)
2025/12/10 11:28:51 NOTICE: Log in and authorize rclone for access
2025/12/10 11:28:51 NOTICE: Waiting for code...
```

**Cause** : Vous êtes dans un conteneur Docker sans navigateur web, et rclone ne peut pas ouvrir automatiquement le navigateur pour l'authentification OAuth.

## ✅ Solutions

### Solution 1 : Annuler et Recommencer (RECOMMANDÉ)

1. **Annulez le processus actuel** :
   - Appuyez sur `Ctrl+C` dans le terminal où rclone attend

2. **Sortez du conteneur Docker** :
   ```bash
   exit
   ```

3. **Configurez rclone sur votre machine locale** (celle avec un navigateur) :
   ```bash
   # Sur votre ordinateur local/Mac/Windows
   curl https://rclone.org/install.sh | bash
   rclone config
   ```

4. **Suivez les étapes de configuration** :
   - name> `gdrive`
   - Storage> `drive`
   - client_id> (appuyez sur Entrée)
   - client_secret> (appuyez sur Entrée)
   - scope> `1`
   - service_account_file> (appuyez sur Entrée)
   - Edit advanced config? `n`
   - Use web browser? `y`
   - Le navigateur s'ouvre → Connectez-vous à Google et autorisez

5. **Récupérez le fichier de configuration** :
   ```bash
   # Sur votre machine locale
   cat ~/.config/rclone/rclone.conf
   ```

6. **Copiez le contenu vers votre serveur** :
   ```bash
   # Option A: Via SCP depuis votre machine locale
   scp ~/.config/rclone/rclone.conf user@votre-serveur:~/.config/rclone/

   # Option B: Copiez le contenu manuellement
   # 1. Affichez le contenu : cat ~/.config/rclone/rclone.conf
   # 2. Sur le serveur : mkdir -p ~/.config/rclone
   # 3. Sur le serveur : nano ~/.config/rclone/rclone.conf
   # 4. Collez le contenu et sauvegardez
   ```

### Solution 2 : Utiliser l'Authentification Manuelle

Si vous ne pouvez pas configurer rclone sur une autre machine :

1. **Annulez le processus actuel** :
   - Appuyez sur `Ctrl+C`

2. **Relancez rclone config avec les bonnes options** :
   ```bash
   rclone config
   ```

3. **IMPORTANT - Répondez différemment** :
   - name> `gdrive`
   - Storage> `drive`
   - client_id> (appuyez sur Entrée)
   - client_secret> (appuyez sur Entrée)
   - scope> `1`
   - service_account_file> (appuyez sur Entrée)
   - Edit advanced config? `n`
   - **Use web browser to automatically authenticate?** → `n` (NON!) ⚠️
   - **Use web browser on a remote headless machine?** → `n` (NON!)

4. **rclone va afficher une URL** comme :
   ```
   Please go to the following link: https://accounts.google.com/o/oauth2/auth?...
   ```

5. **Copiez cette URL complète et ouvrez-la dans votre navigateur** (sur votre ordinateur)

6. **Connectez-vous à Google et autorisez rclone**

7. **Google vous donnera un code** - Copiez ce code

8. **Retournez au terminal et collez le code** quand rclone demande :
   ```
   Enter verification code>
   ```

9. **Confirmez la configuration** :
   - Confirm this is OK? `y`

### Solution 3 : Port Forwarding (Avancé)

Si vous voulez vraiment utiliser l'URL localhost actuelle (http://127.0.0.1:53682/...) :

1. **Depuis VOTRE MACHINE LOCALE**, créez un tunnel SSH :
   ```bash
   ssh -L 53682:localhost:53682 user@votre-serveur
   ```

2. **Dans un autre terminal**, ouvrez l'URL dans votre navigateur local :
   ```
   http://127.0.0.1:53682/auth?state=wJ576MNR8PEMZIDu5L2zrA
   ```
   (Remplacez avec l'URL exacte affichée par rclone)

3. **Authentifiez-vous avec Google**

4. **Retournez au terminal où rclone attend** - il devrait automatiquement recevoir le code

## ⚙️ Vérification de la Configuration

Une fois la configuration terminée, vérifiez qu'elle fonctionne :

```bash
# Lister les remotes configurés
rclone listremotes

# Devrait afficher :
# gdrive:

# Tester la connexion
rclone lsd gdrive:

# Devrait lister vos dossiers Google Drive
```

## 🔍 Emplacements des Fichiers de Configuration

- **Linux/Raspberry Pi** : `~/.config/rclone/rclone.conf`
- **Mac** : `~/.config/rclone/rclone.conf`
- **Windows** : `%USERPROFILE%\.config\rclone\rclone.conf`

## 📝 Notes Importantes

1. **Sécurité** : Le fichier `rclone.conf` contient des tokens d'accès. Gardez-le privé !

2. **Docker Volumes** : Si vous utilisez rclone dans Docker, montez le fichier de config :
   ```yaml
   volumes:
     - ~/.config/rclone:/root/.config/rclone:ro
   ```

3. **Permissions** : Assurez-vous que le fichier est lisible :
   ```bash
   chmod 600 ~/.config/rclone/rclone.conf
   ```

## 🆘 Besoin d'Aide Supplémentaire ?

- Documentation officielle rclone : https://rclone.org/drive/
- Guide de configuration Google Drive : https://rclone.org/drive/#making-your-own-client-id
- Support rclone : https://forum.rclone.org/

## 🎯 Retour au Script d'Installation

Une fois rclone configuré avec succès, vous pouvez :

1. **Tester le backup** :
   ```bash
   ./scripts/backup_to_gdrive.sh
   ```

2. **Relancer le script de sécurité** si vous l'aviez interrompu :
   ```bash
   ./scripts/setup_security.sh
   ```
