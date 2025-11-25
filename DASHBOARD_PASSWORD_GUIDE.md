# 🔐 Guide de gestion du mot de passe Dashboard

Ce guide explique comment configurer, modifier et gérer le mot de passe d'accès au dashboard LinkedIn Birthday Auto Bot.

## 📋 Table des matières

- [Vue d'ensemble](#vue-densemble)
- [Exigences de sécurité](#exigences-de-sécurité)
- [Configuration initiale](#configuration-initiale)
- [Accéder au dashboard](#accéder-au-dashboard)
- [Changer le mot de passe](#changer-le-mot-de-passe)
- [Récupération en cas d'oubli](#récupération-en-cas-doubli)
- [Bonnes pratiques](#bonnes-pratiques)
- [Dépannage](#dépannage)

---

## 🎯 Vue d'ensemble

Le dashboard utilise un système d'authentification basé sur un **mot de passe unique** configuré via la variable d'environnement `DASHBOARD_PASSWORD`.

### Fonctionnement

1. **Page de connexion** : Accessible à `http://IP:3000/login`
2. **Vérification** : Le mot de passe est comparé à `DASHBOARD_PASSWORD`
3. **Token JWT** : Un token sécurisé est généré pour la session (validité : 7 jours)
4. **Cookie HttpOnly** : Le token est stocké de manière sécurisée dans le navigateur

### Utilisation du mot de passe

Le mot de passe `DASHBOARD_PASSWORD` sert à :
- ✅ Authentifier l'accès à l'interface web
- ✅ Générer les tokens JWT (clé de signature)
- ✅ Sécuriser les sessions utilisateur

---

## 🔒 Exigences de sécurité

### Contraintes techniques

| Critère | Valeur | Raison |
|---------|--------|--------|
| **Longueur minimale** | 32 caractères | Exigence JWT pour la sécurité cryptographique |
| **Complexité** | Recommandée | Lettres, chiffres, caractères spéciaux |
| **Stockage** | Fichier .env uniquement | Jamais dans le code source |

### Pourquoi 32 caractères ?

Le mot de passe est utilisé comme **clé secrète JWT (HS256)**. Les standards de sécurité recommandent :
- Minimum : 32 caractères (256 bits)
- Optimal : 64 caractères (512 bits)

---

## 🚀 Configuration initiale

### Étape 1 : Générer un mot de passe sécurisé

#### Option A : Avec OpenSSL (recommandé)

```bash
# Générer 32 caractères hexadécimaux (64 caractères au total)
openssl rand -hex 32

# Exemple de sortie :
# 7f8a9b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9f0a
```

#### Option B : Avec Python

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"

# Exemple de sortie :
# xQ7v9K2mN4pR6sT8uW0yA1cE3gI5jL7nP9qS1tV3xZ5b
```

#### Option C : Avec un générateur en ligne

Utilisez un générateur de mots de passe sécurisé :
- [Password Generator](https://passwordsgenerator.net/) (64 caractères)
- Cochez : Lettres majuscules/minuscules, chiffres, symboles

### Étape 2 : Configurer le fichier .env

#### Pour déploiement Pi4 Standalone

```bash
# Éditer le fichier .env
nano .env

# Ajouter ou modifier la ligne DASHBOARD_PASSWORD
DASHBOARD_PASSWORD=votre_mot_de_passe_généré_ici

# Sauvegarder : Ctrl+O puis Entrée
# Quitter : Ctrl+X
```

#### Pour déploiement Dashboard seul

```bash
# Si vous êtes dans le dossier dashboard/
cd dashboard
nano .env

# Ajouter
DASHBOARD_PASSWORD=votre_mot_de_passe_généré_ici
```

### Étape 3 : Sécuriser le fichier .env

```bash
# Restreindre les permissions (lecture seule par le propriétaire)
chmod 600 .env

# Vérifier
ls -la .env
# Devrait afficher : -rw------- (permissions 600)
```

### Étape 4 : Vérifier la configuration

#### Avant de démarrer les services

```bash
# Vérifier que la variable est définie
grep DASHBOARD_PASSWORD .env

# Vérifier la longueur (doit être >= 32)
echo $DASHBOARD_PASSWORD | wc -c
```

#### Après démarrage du dashboard

```bash
# Vérifier les logs du conteneur
docker logs linkedin-dashboard 2>&1 | grep -i password

# Si erreur "DASHBOARD_PASSWORD must be set", le mot de passe n'est pas configuré
# Si pas d'erreur, la configuration est OK
```

---

## 🌐 Accéder au dashboard

### Première connexion

1. **Obtenir l'IP du Pi4** (ou serveur) :
   ```bash
   hostname -I
   # Exemple : 192.168.1.50
   ```

2. **Ouvrir le navigateur** et aller à :
   ```
   http://192.168.1.50:3000/login
   ```

3. **Saisir le mot de passe** configuré dans `DASHBOARD_PASSWORD`

4. **Connexion réussie** : Vous êtes redirigé vers `/` (page d'accueil du dashboard)

### Sessions

- **Durée** : 7 jours (configurable dans `dashboard/app/api/login/route.ts:29`)
- **Cookie** : `auth_token` (HttpOnly, Secure en production)
- **Déconnexion automatique** : Après 7 jours ou suppression des cookies

---

## 🔄 Changer le mot de passe

### Scénario 1 : Déploiement Pi4 avec Docker

```bash
# 1. Se connecter au Pi4
ssh pi@192.168.1.50

# 2. Aller dans le dossier du projet
cd ~/linkedin-birthday-auto

# 3. Générer un nouveau mot de passe
NEW_PASSWORD=$(openssl rand -hex 32)
echo "Nouveau mot de passe : $NEW_PASSWORD"

# 4. Sauvegarder dans un endroit sûr (gestionnaire de mots de passe)
# ⚠️ Copiez ce mot de passe maintenant, vous en aurez besoin pour vous connecter !

# 5. Éditer le fichier .env
nano .env
# Modifier la ligne DASHBOARD_PASSWORD avec le nouveau mot de passe

# 6. Redémarrer le service dashboard
docker compose -f docker-compose.pi4-standalone.yml restart dashboard

# 7. Vérifier les logs
docker logs linkedin-dashboard --tail 50

# 8. Tester la connexion
# Ouvrir http://192.168.1.50:3000/login et utiliser le nouveau mot de passe
```

### Scénario 2 : Déploiement Dashboard standalone

```bash
# 1. Aller dans le dossier dashboard
cd dashboard

# 2. Éditer .env
nano .env

# 3. Modifier DASHBOARD_PASSWORD

# 4. Redémarrer
docker compose restart app

# 5. Vérifier
docker logs linkedin_dashboard
```

### Scénario 3 : Sans Docker (développement local)

```bash
# 1. Éditer .env
nano .env

# 2. Modifier DASHBOARD_PASSWORD

# 3. Redémarrer le serveur Next.js
# Si lancé avec npm run dev : Ctrl+C puis npm run dev
# Si lancé avec npm start : Ctrl+C puis npm start
```

### Impact du changement

- ✅ **Sessions actives invalidées** : Tous les utilisateurs connectés devront se reconnecter
- ✅ **Tokens JWT invalidés** : Les anciens tokens ne fonctionneront plus
- ⚠️ **Pas de migration automatique** : Il faut se reconnecter manuellement

---

## 🆘 Récupération en cas d'oubli

Si vous avez oublié votre mot de passe, suivez ces étapes :

### Méthode 1 : Consulter le fichier .env

```bash
# Se connecter au serveur
ssh pi@192.168.1.50

# Afficher le mot de passe
cat ~/linkedin-birthday-auto/.env | grep DASHBOARD_PASSWORD

# Ou avec Docker
docker exec linkedin-dashboard printenv DASHBOARD_PASSWORD
```

### Méthode 2 : Réinitialiser le mot de passe

```bash
# 1. Générer un nouveau mot de passe
NEW_PASSWORD=$(openssl rand -hex 32)
echo "Nouveau mot de passe : $NEW_PASSWORD"

# 2. Éditer .env
cd ~/linkedin-birthday-auto
nano .env
# Remplacer DASHBOARD_PASSWORD

# 3. Redémarrer le dashboard
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

### Méthode 3 : Accès via console Docker (debug uniquement)

```bash
# Accéder au conteneur
docker exec -it linkedin-dashboard /bin/sh

# Afficher la variable d'environnement
echo $DASHBOARD_PASSWORD

# Quitter
exit
```

---

## ✅ Bonnes pratiques

### Gestion du mot de passe

1. **Utiliser un gestionnaire de mots de passe**
   - Recommandé : Bitwarden, 1Password, KeePass
   - Sauvegarder le mot de passe avec l'URL du dashboard

2. **Ne jamais partager le mot de passe**
   - ❌ Ne pas envoyer par email, SMS, ou chat
   - ✅ Partager via un gestionnaire sécurisé (ex : Bitwarden Send)

3. **Changer régulièrement**
   - Recommandation : Tous les 6 mois minimum
   - Obligatoire si suspicion de compromission

4. **Sauvegarder le fichier .env de manière sécurisée**
   ```bash
   # Copier .env dans un emplacement sécurisé
   cp .env .env.backup.$(date +%Y%m%d)

   # Chiffrer la sauvegarde (optionnel)
   gpg -c .env.backup.20240101
   ```

### Sécurité réseau

1. **Accès local uniquement** (recommandé)
   - Pas d'exposition sur Internet public
   - Accès via VPN si nécessaire (Wireguard, OpenVPN)

2. **HTTPS avec reverse proxy** (avancé)
   - Nginx/Traefik avec Let's Encrypt
   - Configuration dans [SETUP_PI4_FREEBOX.md](SETUP_PI4_FREEBOX.md)

3. **Firewall actif**
   ```bash
   # Bloquer le port 3000 depuis l'extérieur
   sudo ufw allow from 192.168.1.0/24 to any port 3000
   sudo ufw deny 3000
   ```

---

## 🐛 Dépannage

### Problème : "DASHBOARD_PASSWORD is not set on the server"

**Cause** : La variable `DASHBOARD_PASSWORD` n'est pas définie ou vide.

**Solution** :

```bash
# Vérifier si la variable existe
grep DASHBOARD_PASSWORD .env

# Si vide ou inexistante, ajouter
echo "DASHBOARD_PASSWORD=$(openssl rand -hex 32)" >> .env

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

### Problème : "DASHBOARD_PASSWORD must be at least 32 characters long"

**Cause** : Le mot de passe est trop court (< 32 caractères).

**Solution** :

```bash
# Générer un mot de passe de 32+ caractères
openssl rand -hex 32

# Mettre à jour .env
nano .env
# Remplacer DASHBOARD_PASSWORD par le nouveau

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

### Problème : "Incorrect password" à chaque tentative

**Cause 1** : Mot de passe incorrect
- Vérifier que vous utilisez le bon mot de passe depuis .env

**Cause 2** : Espaces ou caractères invisibles
```bash
# Vérifier le mot de passe exact (sans espaces)
cat .env | grep DASHBOARD_PASSWORD | cat -A
# Les espaces apparaissent comme $ en fin de ligne

# Corriger si nécessaire
nano .env
```

**Cause 3** : Variable non chargée par Docker
```bash
# Vérifier que la variable est passée au conteneur
docker exec linkedin-dashboard printenv DASHBOARD_PASSWORD

# Si vide, vérifier docker-compose*.yml
grep DASHBOARD_PASSWORD docker-compose*.yml
```

### Problème : Le dashboard ne démarre pas après ajout du mot de passe

**Vérifier les logs** :
```bash
docker logs linkedin-dashboard

# Erreurs possibles :
# - "Error: DASHBOARD_PASSWORD environment variable must be set"
# - "TypeError: Cannot read property 'length' of undefined"
```

**Solution** :
```bash
# Vérifier le fichier docker-compose
cat docker-compose.pi4-standalone.yml | grep -A 5 DASHBOARD_PASSWORD

# S'assurer que la ligne est :
# - DASHBOARD_PASSWORD=${DASHBOARD_PASSWORD}

# Redémarrer avec reconstruction
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate dashboard
```

### Problème : Token JWT invalide après connexion réussie

**Cause** : Le mot de passe a changé après génération du token.

**Solution** :
```bash
# Supprimer les cookies dans le navigateur
# Chrome : F12 > Application > Cookies > Supprimer auth_token

# Ou utiliser une fenêtre de navigation privée
```

### Problème : Accès refusé après 7 jours

**Cause** : La session JWT a expiré (durée par défaut : 7 jours).

**Solution** :
- Se reconnecter via `/login`

**Modifier la durée** (optionnel) :
```bash
# Éditer dashboard/app/api/login/route.ts ligne 29
# Changer 7d en 30d pour 30 jours
.setExpirationTime('30d')

# Reconstruire l'image Docker
docker compose -f docker-compose.pi4-standalone.yml build dashboard
docker compose -f docker-compose.pi4-standalone.yml up -d dashboard
```

---

## 📚 Références

- **Fichiers de configuration** :
  - `.env.pi4` : Template de configuration Pi4
  - `docker-compose.pi4-standalone.yml` : Configuration Docker complète
  - `dashboard/docker-compose.yml` : Configuration Dashboard standalone

- **Code source** :
  - `dashboard/app/api/login/route.ts` : Logique d'authentification
  - `dashboard/middleware.ts` : Vérification des tokens JWT
  - `dashboard/app/login/page.tsx` : Page de connexion

- **Documentation connexe** :
  - [SETUP_PI4_FREEBOX.md](SETUP_PI4_FREEBOX.md) : Déploiement complet Pi4
  - [DEPLOYMENT.md](DEPLOYMENT.md) : Guides de déploiement généraux
  - [README.md](README.md) : Vue d'ensemble du projet

---

## 🔐 Rappels de sécurité

- ✅ **Toujours** utiliser un mot de passe de 32+ caractères
- ✅ **Jamais** committer le fichier `.env` dans Git (déjà dans `.gitignore`)
- ✅ **Toujours** restreindre les permissions : `chmod 600 .env`
- ✅ **Sauvegarder** le mot de passe dans un gestionnaire sécurisé
- ✅ **Changer** le mot de passe par défaut avant le premier déploiement
- ✅ **Utiliser** un VPN pour accès distant au dashboard
- ⚠️ **Ne pas exposer** le port 3000 directement sur Internet

---

**Besoin d'aide ?**
- Issues GitHub : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
- Documentation : Voir les autres fichiers `.md` du projet
