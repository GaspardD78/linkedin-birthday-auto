# Guide d'authentification du Dashboard

Le dashboard LinkedIn Birthday Auto Bot supporte **deux méthodes d'authentification** :

1. **Google OAuth** - Connexion avec un compte Google (recommandé)
2. **Username/Password** - Connexion traditionnelle par identifiants

Les deux méthodes peuvent être utilisées simultanément ou indépendamment.

## 🎯 Aperçu

### Page de connexion

La page de connexion (`/login`) propose :
- Un bouton **"Continuer avec Google"** en haut
- Un séparateur "OU"
- Un formulaire **Username/Password** en bas

Les utilisateurs peuvent choisir librement leur méthode préférée.

## 🔐 Méthode 1 : Google OAuth (Recommandé)

### Avantages
- ✅ Pas besoin de mémoriser un mot de passe supplémentaire
- ✅ Authentification sécurisée gérée par Google
- ✅ Support de l'authentification multi-facteurs (2FA) Google
- ✅ Connexion rapide en un clic

### Configuration

1. **Obtenir les credentials Google OAuth**
   - Suivez le guide complet : [GOOGLE_OAUTH_SETUP.md](./GOOGLE_OAUTH_SETUP.md)
   - Vous obtiendrez un `GOOGLE_CLIENT_ID` et un `GOOGLE_CLIENT_SECRET`

2. **Configurer les variables d'environnement**

   Éditez `dashboard/.env` :
   ```bash
   # NextAuth Secret (générez avec: openssl rand -hex 32)
   AUTH_SECRET=votre_secret_nextauth_32_chars_minimum

   # NextAuth Base URL
   NEXTAUTH_URL=http://localhost:3000

   # Google OAuth Credentials
   GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
   ```

3. **Redémarrer le dashboard**
   ```bash
   docker-compose restart dashboard
   ```

4. **Se connecter**
   - Allez sur `http://localhost:3000/login`
   - Cliquez sur **"Continuer avec Google"**
   - Sélectionnez votre compte Google
   - Autorisez l'application
   - Vous êtes connecté ! ✅

### Restriction d'accès (Optionnel)

Par défaut, **n'importe quel compte Google** peut se connecter.

Pour restreindre l'accès, modifiez `dashboard/auth.config.ts` :

#### Limiter à des emails spécifiques
```typescript
const ALLOWED_EMAILS = [
  "admin@example.com",
  "user@example.com",
];

callbacks: {
  async signIn({ user, account }) {
    if (account?.provider === "google") {
      if (!ALLOWED_EMAILS.includes(user.email || "")) {
        return false; // Refuse la connexion
      }
    }
    return true;
  },
  // ... autres callbacks
}
```

#### Limiter à un domaine d'entreprise
```typescript
callbacks: {
  async signIn({ user, account }) {
    if (account?.provider === "google") {
      if (!user.email?.endsWith("@votreentreprise.com")) {
        return false;
      }
    }
    return true;
  },
  // ... autres callbacks
}
```

## 🔑 Méthode 2 : Username/Password

### Avantages
- ✅ Fonctionne sans compte Google
- ✅ Configuration simple
- ✅ Contrôle total sur les credentials

### Configuration

1. **Configurer les variables d'environnement**

   Éditez `dashboard/.env` :
   ```bash
   # JWT Secret pour validation (legacy)
   JWT_SECRET=votre_jwt_secret_32_chars_minimum

   # NextAuth Secret
   AUTH_SECRET=votre_secret_nextauth_32_chars_minimum

   # Credentials de connexion
   DASHBOARD_USER=votre_username
   DASHBOARD_PASSWORD=votre_password_ou_hash_bcrypt
   ```

2. **Option : Hasher le mot de passe (Recommandé)**

   Pour plus de sécurité, hashez votre mot de passe avec bcrypt :

   ```bash
   # Générer un hash bcrypt
   cd dashboard
   node -e "const bcrypt = require('bcryptjs'); console.log(bcrypt.hashSync('VotreMotDePasse', 10));"
   ```

   Utilisez le hash généré (commence par `$2a$` ou `$2b$`) dans `DASHBOARD_PASSWORD`.

3. **Redémarrer le dashboard**
   ```bash
   docker-compose restart dashboard
   ```

4. **Se connecter**
   - Allez sur `http://localhost:3000/login`
   - Entrez votre username et password
   - Cliquez sur **"Se connecter"**
   - Vous êtes connecté ! ✅

## 🔄 Utiliser les deux méthodes simultanément

C'est la configuration **par défaut** et **recommandée** !

Configurez simplement :
- Les variables Google OAuth (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`)
- Les credentials username/password (`DASHBOARD_USER`, `DASHBOARD_PASSWORD`)
- Les secrets (`AUTH_SECRET`, `JWT_SECRET`)

Les utilisateurs pourront choisir leur méthode préférée sur la page de connexion.

## ⚙️ Variables d'environnement requises

### Configuration minimale (Username/Password uniquement)

```bash
# Secrets
JWT_SECRET=<32+ caractères>
AUTH_SECRET=<32+ caractères>
NEXTAUTH_URL=http://localhost:3000

# Credentials
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=votre_password
```

### Configuration complète (Google + Username/Password)

```bash
# Secrets
JWT_SECRET=<32+ caractères>
AUTH_SECRET=<32+ caractères>
NEXTAUTH_URL=http://localhost:3000

# Credentials traditionnels
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=votre_password

# Google OAuth
GOOGLE_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-xxxxx
```

### Génération des secrets

```bash
# Générer AUTH_SECRET
openssl rand -hex 32

# Générer JWT_SECRET
openssl rand -hex 32

# Générer hash bcrypt pour DASHBOARD_PASSWORD
node -e "console.log(require('bcryptjs').hashSync('VotrePassword', 10))"
```

## 🔒 Sécurité

### Sessions

- **Durée** : 24 heures
- **Type** : JWT (JSON Web Token)
- **Stockage** : Cookie HttpOnly (protection XSS)
- **Chiffrement** : HS256 avec `AUTH_SECRET`

### Protection CSRF

- NextAuth.js intègre une protection CSRF automatique
- Tokens CSRF générés pour chaque session

### Protection des cookies

```typescript
{
  httpOnly: true,    // Protection XSS
  sameSite: "lax",   // Protection CSRF
  secure: true,      // HTTPS uniquement (production)
}
```

## 🚪 Déconnexion

Pour se déconnecter :
1. Cliquez sur votre profil en haut à droite (si implémenté)
2. Ou allez directement sur `/api/auth/signout`
3. Confirmez la déconnexion

## 🛠️ Développement

### Structure des fichiers

```
dashboard/
├── auth.ts                    # Configuration NextAuth principale
├── auth.config.ts             # Configuration providers et callbacks
├── middleware.ts              # Protection des routes
├── app/
│   ├── login/
│   │   ├── page.tsx          # Page de connexion
│   │   └── actions.ts        # Actions serveur
│   └── api/
│       └── auth/
│           └── [...nextauth]/
│               └── route.ts  # Routes API NextAuth
├── lib/
│   └── auth.ts               # Fonctions utilitaires (JWT, bcrypt)
└── types/
    └── next-auth.d.ts        # Types TypeScript étendus
```

### Tester l'authentification

```bash
# Développement local
npm run dev

# Build de production
npm run build
npm run start
```

### Logs de débogage

NextAuth.js affiche des logs détaillés en mode développement :
- Tentatives de connexion
- Callbacks exécutés
- Tokens JWT générés
- Erreurs d'authentification

## 📱 Authentification en production

### Configuration HTTPS

En production, **HTTPS est obligatoire** pour Google OAuth.

```bash
NEXTAUTH_URL=https://votredomaine.com
```

### URI de redirection Google

Ajoutez dans Google Cloud Console :
```
https://votredomaine.com/api/auth/callback/google
```

### Variables d'environnement Docker

Dans `docker-compose.yml` :

```yaml
services:
  dashboard:
    environment:
      - AUTH_SECRET=${AUTH_SECRET}
      - NEXTAUTH_URL=${NEXTAUTH_URL}
      - GOOGLE_CLIENT_ID=${GOOGLE_CLIENT_ID}
      - GOOGLE_CLIENT_SECRET=${GOOGLE_CLIENT_SECRET}
      - DASHBOARD_USER=${DASHBOARD_USER}
      - DASHBOARD_PASSWORD=${DASHBOARD_PASSWORD}
```

## ❓ FAQ

### Puis-je désactiver Google OAuth ?

Oui, ne définissez simplement pas `GOOGLE_CLIENT_ID` et `GOOGLE_CLIENT_SECRET`. Le bouton Google ne s'affichera pas.

### Puis-je désactiver Username/Password ?

Techniquement oui, mais **non recommandé**. Gardez toujours une méthode de secours au cas où Google OAuth aurait un problème.

### Les sessions sont-elles partagées entre les deux méthodes ?

Oui, une fois connecté (par Google ou Username/Password), vous avez la même session et les mêmes permissions.

### Comment changer le mot de passe username/password ?

1. Générez un nouveau hash : `node -e "console.log(require('bcryptjs').hashSync('NouveauPassword', 10))"`
2. Mettez à jour `DASHBOARD_PASSWORD` dans `.env`
3. Redémarrez le dashboard

### Comment révoquer l'accès à tous les utilisateurs ?

Changez `AUTH_SECRET` dans `.env` et redémarrez. Toutes les sessions seront invalidées.

## 🐛 Dépannage

### "Erreur de connexion au serveur"

**Cause** : Variables d'environnement manquantes

**Solution** :
```bash
# Vérifiez que les variables sont définies
docker-compose exec dashboard env | grep -E '(AUTH_SECRET|DASHBOARD_USER|DASHBOARD_PASSWORD)'
```

### "Invalid credentials"

**Cause** : Username ou password incorrect

**Solution** : Vérifiez `DASHBOARD_USER` et `DASHBOARD_PASSWORD` dans `.env`

### Le bouton Google ne fonctionne pas

**Causes possibles** :
1. `GOOGLE_CLIENT_ID` ou `GOOGLE_CLIENT_SECRET` manquant/invalide
2. URI de redirection non configuré dans Google Cloud Console
3. `AUTH_SECRET` manquant

**Solution** : Suivez [GOOGLE_OAUTH_SETUP.md](./GOOGLE_OAUTH_SETUP.md)

## 📚 Ressources

- [Documentation NextAuth.js](https://next-auth.js.org/)
- [Guide Google OAuth](./GOOGLE_OAUTH_SETUP.md)
- [Variables d'environnement](../dashboard/.env.example)

---

**Besoin d'aide ?** Ouvrez une issue sur GitHub avec le tag `authentication`.
