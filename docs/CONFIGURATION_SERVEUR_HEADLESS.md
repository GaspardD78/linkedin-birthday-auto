# Configuration du Bot LinkedIn sur Serveur Headless

Guide complet pour configurer le bot LinkedIn Birthday sur un serveur sans navigateur (headless), comme un Raspberry Pi ou un serveur Linux distant.

## 📋 Table des matières

1. [Problèmes courants](#problèmes-courants)
2. [Initialisation du fichier .env](#1-initialisation-du-fichier-env)
3. [Configuration Google Drive sans navigateur](#2-configuration-google-drive-sans-navigateur)
4. [Vérification de la sécurité](#3-vérification-de-la-sécurité)
5. [Résolution des problèmes](#résolution-des-problèmes)

---

## Problèmes courants

### Le script de sécurité échoue toujours

Si vous voyez ces erreurs à répétition :

```
[3] Connexion à Google Drive... ✗ FAIL
    → Impossible de se connecter à Google Drive

[22] Mot de passe hashé dans .env... ✗ FAIL
    → Mot de passe EN CLAIR - hashez avec: node dashboard/scripts/hash_password.js
```

**Causes :**
- Le fichier `.env` n'existe pas ou est mal configuré
- Google Drive nécessite une configuration spéciale sans navigateur

**Solution :**
Suivez ce guide dans l'ordre ci-dessous.

---

## 1. Initialisation du fichier .env

### Pourquoi cette étape ?

Le fichier `.env` contient toutes les variables de configuration sensibles :
- Clés API secrètes
- Mot de passe du dashboard (qui DOIT être hashé)
- Configuration de la base de données
- Configuration CORS

### Comment faire ?

```bash
# Depuis la racine du projet
./scripts/init_env.sh
```

### Ce que fait le script

1. **Copie le fichier exemple** `.env.pi4.example` → `.env`
2. **Génère automatiquement** les clés secrètes :
   - `API_KEY` (64 caractères aléatoires)
   - `JWT_SECRET` (64 caractères aléatoires)
3. **Configure le mot de passe** :
   - Demande votre nom d'utilisateur (défaut : `admin`)
   - Demande votre mot de passe (minimum 8 caractères)
   - **Hash automatiquement** le mot de passe avec bcrypt
4. **Configure CORS** (optionnel) pour l'accès depuis votre domaine

### Vérification

Après l'exécution, vérifiez que le mot de passe est bien hashé :

```bash
grep "^DASHBOARD_PASSWORD=" .env
```

✅ **Bon** : Le mot de passe commence par `$2a$` ou `$2b$`
```
DASHBOARD_PASSWORD=$2b$12$kQX5Z3JvHJ8pZm0nQqF0c.XYZ123...
```

❌ **Mauvais** : Le mot de passe est en clair
```
DASHBOARD_PASSWORD=MonMotDePasse123
```

---

## 2. Configuration Google Drive sans navigateur

### Le problème

Google Drive utilise OAuth2 qui nécessite un navigateur web pour autoriser l'accès. Sur un serveur headless (sans navigateur), cette méthode ne fonctionne pas.

### La solution : Configuration à distance

Vous devez configurer rclone sur un ordinateur **avec navigateur**, puis transférer la configuration sur le serveur.

### Étape par étape

#### Sur votre PC local (Windows, Mac, ou Linux avec interface)

**1. Installez rclone**

- **Windows** : Téléchargez sur https://rclone.org/downloads/
- **Mac** : `brew install rclone`
- **Linux** : `sudo apt install rclone`

**2. Configurez Google Drive**

```bash
rclone config
```

Suivez ces étapes :

```
n)  New remote
name> gdrive
Type of storage> 15  (Google Drive)
client_id> [Laissez vide - Appuyez sur Entrée]
client_secret> [Laissez vide - Appuyez sur Entrée]
scope> 1  (Full access)
root_folder_id> [Laissez vide]
service_account_file> [Laissez vide]
Edit advanced config? n
Use auto config? y  ← IMPORTANT : Cela ouvre le navigateur
```

→ Une page web s'ouvre : **Autorisez l'accès à Google Drive**

```
Configure this as a team drive? n
Yes this is OK> y
```

**3. Localisez le fichier de configuration**

- **Windows** : `%USERPROFILE%\.config\rclone\rclone.conf`
- **Mac/Linux** : `~/.config/rclone/rclone.conf`

**4. Transférez le fichier sur le serveur**

Plusieurs méthodes possibles :

##### Méthode A : Par SCP (recommandé)

```bash
# Depuis votre PC
scp ~/.config/rclone/rclone.conf user@votre-serveur:/tmp/rclone.conf
```

##### Méthode B : Copier-coller le contenu

Sur votre PC :
```bash
cat ~/.config/rclone/rclone.conf
```

Copiez tout le contenu, puis sur le serveur :
```bash
mkdir -p ~/.config/rclone
nano ~/.config/rclone/rclone.conf
# Collez le contenu
# Ctrl+O pour sauvegarder, Ctrl+X pour quitter
chmod 600 ~/.config/rclone/rclone.conf
```

#### Sur le serveur

**Lancez le script d'import**

```bash
./scripts/setup_gdrive_headless.sh
```

Le script va :
1. ✅ Vérifier/installer rclone
2. 📋 Afficher les instructions détaillées
3. 📥 Importer votre fichier rclone.conf
4. 🔗 Tester la connexion à Google Drive

### Vérification manuelle

```bash
# Lister les fichiers Google Drive
rclone lsd gdrive:

# Tester un upload
echo "test" > /tmp/test.txt
rclone copy /tmp/test.txt gdrive:backups/
```

---

## 3. Vérification de la sécurité

Une fois les étapes 1 et 2 terminées :

```bash
./scripts/verify_security.sh
```

### Résultat attendu

```
📦 SECTION 1/7 : BACKUP GOOGLE DRIVE
  [1] rclone installé... ✓ PASS
  [2] Remote Google Drive configuré... ✓ PASS
  [3] Connexion à Google Drive... ✓ PASS  ← DOIT être ✓

🔑 SECTION 4/7 : MOT DE PASSE HASHÉ BCRYPT
  [22] Mot de passe hashé dans .env... ✓ PASS  ← DOIT être ✓
```

### Score de sécurité

- **≥ 90%** : 🏆 Excellent - Tout est correct
- **70-89%** : ⚠️  Bon - Quelques améliorations possibles
- **< 70%** : ❌ Insuffisant - Actions requises

---

## Résolution des problèmes

### ❌ "Connexion à Google Drive... ✗ FAIL"

**Diagnostic :**
```bash
rclone lsd gdrive: 2>&1
```

**Solutions possibles :**

1. **Token expiré**
   - Re-générez le fichier `rclone.conf` sur votre PC
   - Transférez-le à nouveau sur le serveur

2. **Remote mal configuré**
   ```bash
   rclone config show gdrive
   ```
   Vérifiez que le remote s'appelle bien `gdrive:`

3. **Problème de permissions**
   ```bash
   chmod 600 ~/.config/rclone/rclone.conf
   ```

### ❌ "Mot de passe EN CLAIR"

**Solution rapide :**

```bash
# Re-lancer l'initialisation
./scripts/init_env.sh
```

**Solution manuelle :**

```bash
# 1. Installer bcryptjs
cd dashboard
npm install bcryptjs

# 2. Hasher votre mot de passe
node scripts/hash_password.js "VotreMotDePasse123"

# 3. Copier le hash dans .env
nano .env
# Remplacer la ligne DASHBOARD_PASSWORD= par le hash généré
```

### ⚠️ "Header manquant (normal si pas de HTTPS)"

C'est normal si vous n'avez pas encore configuré le certificat SSL.

**Pour activer HTTPS :**

```bash
# 1. Avoir un nom de domaine pointant vers votre serveur
# 2. Installer le certificat Let's Encrypt
sudo certbot --nginx -d votre-domaine.com
```

### 🔍 Fichier .env perdu ou corrompu

**Récupérer depuis un backup :**

```bash
# Lister les backups
ls -lh .env.backup.*

# Restaurer le plus récent
cp .env.backup.YYYYMMDD_HHMMSS .env
```

**Repartir de zéro :**

```bash
rm .env
./scripts/init_env.sh
```

---

## 📝 Checklist complète

Avant de démarrer le bot, assurez-vous que :

- [ ] Le fichier `.env` existe
- [ ] Le mot de passe dans `.env` est hashé (commence par `$2a$` ou `$2b$`)
- [ ] Les clés `API_KEY` et `JWT_SECRET` sont générées (64 caractères)
- [ ] rclone est installé (`rclone version`)
- [ ] Le remote `gdrive:` est configuré (`rclone listremotes`)
- [ ] La connexion Google Drive fonctionne (`rclone lsd gdrive:`)
- [ ] Le script de sécurité passe tous les tests critiques
- [ ] Les permissions du .env sont correctes (`chmod 600 .env`)

---

## 🚀 Démarrage

Une fois tout configuré :

```bash
# Démarrer les conteneurs
docker compose up -d

# Vérifier les logs
docker compose logs -f

# Accéder au dashboard
# http://VOTRE_IP:3000
```

---

## 📞 Support

En cas de problème persistant :

1. **Vérifiez les logs** : `docker compose logs -f`
2. **Consultez les issues GitHub** : https://github.com/GaspardD78/linkedin-birthday-auto/issues
3. **Relancez la vérification** : `./scripts/verify_security.sh --fix`

---

**Dernière mise à jour** : 2025-12-10
