# Configuration Google OAuth pour le Dashboard

Ce guide vous explique comment configurer l'authentification Google OAuth pour le dashboard LinkedIn Birthday Auto Bot.

## 📋 Prérequis

- Un compte Google
- Accès à Google Cloud Console
- Variables d'environnement de base configurées (voir `dashboard/.env.example`)

## 🚀 Étapes de configuration

### 1. Créer un projet Google Cloud

1. Rendez-vous sur [Google Cloud Console](https://console.cloud.google.com/)
2. Cliquez sur le sélecteur de projet en haut de la page
3. Cliquez sur **"Nouveau projet"**
4. Donnez un nom à votre projet (ex: "LinkedIn Bot Dashboard")
5. Cliquez sur **"Créer"**

### 2. Activer l'API Google+

1. Dans le menu de navigation, allez dans **"API et services"** > **"Bibliothèque"**
2. Recherchez "Google+ API"
3. Cliquez dessus et cliquez sur **"Activer"**

### 3. Configurer l'écran de consentement OAuth

1. Dans le menu de navigation, allez dans **"API et services"** > **"Écran de consentement OAuth"**
2. Sélectionnez **"Externe"** (sauf si vous avez un compte Google Workspace)
3. Cliquez sur **"Créer"**
4. Remplissez les informations requises :
   - **Nom de l'application** : "LinkedIn Birthday Bot Dashboard"
   - **E-mail d'assistance utilisateur** : votre email
   - **Logo de l'application** : optionnel
   - **Domaine de l'application** : votre domaine (si applicable)
   - **E-mail du développeur** : votre email
5. Cliquez sur **"Enregistrer et continuer"**
6. **Étape "Champs d'application"** : Cliquez sur **"Enregistrer et continuer"** (les champs par défaut suffisent)
7. **Étape "Utilisateurs test"** : Ajoutez les adresses email autorisées (si mode test)
8. Cliquez sur **"Enregistrer et continuer"**

### 4. Créer les identifiants OAuth 2.0

1. Dans le menu de navigation, allez dans **"API et services"** > **"Identifiants"**
2. Cliquez sur **"Créer des identifiants"** > **"ID client OAuth"**
3. Sélectionnez **"Application Web"**
4. Configurez les paramètres :
   - **Nom** : "LinkedIn Bot Dashboard Web Client"
   - **Origines JavaScript autorisées** :
     ```
     http://localhost:3000
     ```
     (Ajoutez votre domaine de production si applicable)

   - **URI de redirection autorisés** :
     ```
     http://localhost:3000/api/auth/callback/google
     ```
     (Remplacez `localhost:3000` par votre domaine en production)

5. Cliquez sur **"Créer"**
6. **IMPORTANT** : Copiez immédiatement les valeurs suivantes :
   - **ID client** (ressemble à : `xxxxx.apps.googleusercontent.com`)
   - **Secret client** (ressemble à : `GOCSPX-xxxxx`)

### 5. Configurer les variables d'environnement

1. Ouvrez votre fichier `.env` dans le dossier `dashboard/`
2. Ajoutez ou mettez à jour les variables suivantes :

```bash
# NextAuth Secret (générez avec: openssl rand -hex 32)
AUTH_SECRET=votre_secret_nextauth_minimum_32_caracteres

# NextAuth Base URL
NEXTAUTH_URL=http://localhost:3000

# Google OAuth Credentials
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

3. Sauvegardez le fichier

### 6. Redémarrer le dashboard

```bash
# Si vous utilisez Docker Compose
docker-compose restart dashboard

# Ou si vous utilisez npm en développement
cd dashboard
npm run dev
```

## ✅ Tester l'authentification

1. Rendez-vous sur `http://localhost:3000/login`
2. Vous devriez voir deux options :
   - **"Continuer avec Google"** (bouton blanc avec logo Google)
   - **Formulaire username/password** (méthode traditionnelle)
3. Cliquez sur **"Continuer avec Google"**
4. Sélectionnez votre compte Google
5. Autorisez l'application
6. Vous devriez être redirigé vers le dashboard

## 🔒 Configuration de production

### URL de production

Pour un environnement de production, mettez à jour vos variables :

```bash
NEXTAUTH_URL=https://votredomaine.com
```

### URI de redirection en production

Dans Google Cloud Console, ajoutez l'URI de production :

```
https://votredomaine.com/api/auth/callback/google
```

### Origines JavaScript autorisées

Ajoutez votre domaine de production :

```
https://votredomaine.com
```

## 🛡️ Sécurité

### Mode Test vs Production

- **Mode Test** : Seulement les utilisateurs test peuvent se connecter
- **Mode Production** : Nécessite une vérification par Google (processus de publication)

Pour passer en production :
1. Allez dans **"Écran de consentement OAuth"**
2. Cliquez sur **"Publier l'application"**
3. Suivez le processus de vérification de Google

### Restriction par domaine (recommandé pour production)

Si vous voulez limiter l'accès à un domaine spécifique (ex: `@votreentreprise.com`), modifiez le fichier `dashboard/auth.config.ts` :

```typescript
// Dans le callback signIn
async signIn({ user, account, profile }) {
  if (account?.provider === "google") {
    // Autoriser seulement les emails du domaine spécifique
    if (!user.email?.endsWith("@votreentreprise.com")) {
      return false; // Refuser la connexion
    }
  }
  return true;
},
```

### Limiter à des emails spécifiques

Pour limiter à des emails spécifiques :

```typescript
const ALLOWED_EMAILS = [
  "user1@gmail.com",
  "user2@gmail.com",
];

async signIn({ user, account, profile }) {
  if (account?.provider === "google") {
    if (!ALLOWED_EMAILS.includes(user.email || "")) {
      return false;
    }
  }
  return true;
},
```

## 🐛 Dépannage

### Erreur "redirect_uri_mismatch"

**Cause** : L'URI de redirection n'est pas configurée dans Google Cloud Console

**Solution** :
1. Vérifiez que `http://localhost:3000/api/auth/callback/google` est bien dans les URI autorisés
2. Assurez-vous qu'il n'y a pas d'espace ou de caractère supplémentaire
3. Attendez quelques minutes après avoir ajouté l'URI (propagation)

### Erreur "Access blocked: This app's request is invalid"

**Cause** : L'écran de consentement n'est pas configuré ou incomplet

**Solution** :
1. Retournez à **"Écran de consentement OAuth"**
2. Vérifiez que toutes les informations requises sont remplies
3. Assurez-vous que l'email d'assistance est valide

### Le bouton Google ne s'affiche pas

**Cause** : Variables d'environnement manquantes ou invalides

**Solution** :
1. Vérifiez que `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET` sont bien définis
2. Vérifiez que `AUTH_SECRET` est défini (minimum 32 caractères)
3. Redémarrez le serveur après modification du `.env`

### Erreur "NEXTAUTH_URL" en production

**Cause** : La variable `NEXTAUTH_URL` pointe vers localhost

**Solution** :
1. Mettez à jour `NEXTAUTH_URL=https://votredomaine.com`
2. Redéployez l'application

## 📚 Ressources

- [Documentation NextAuth.js](https://next-auth.js.org/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)

## ❓ Questions fréquentes

### Puis-je désactiver Google OAuth et garder seulement username/password ?

Oui, il suffit de ne pas définir `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET`. Le bouton Google ne s'affichera pas.

### Puis-je autoriser n'importe quel compte Google ?

Oui, c'est la configuration par défaut actuelle. Pour restreindre l'accès, voir la section "Sécurité" ci-dessus.

### Les deux méthodes (Google + username/password) fonctionnent-elles en même temps ?

Oui, les deux méthodes sont complètement indépendantes et peuvent être utilisées simultanément.

### Comment révoquer l'accès Google d'un utilisateur ?

1. Allez sur [Google Account Permissions](https://myaccount.google.com/permissions)
2. Trouvez "LinkedIn Birthday Bot Dashboard"
3. Cliquez sur "Remove Access"

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub avec le tag `authentication`.
