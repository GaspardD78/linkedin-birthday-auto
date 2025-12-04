# LinkedIn Birthday Bot - Dashboard

Dashboard web moderne pour gérer et monitorer le bot LinkedIn Birthday Auto.

## 🚀 Démarrage Rapide

### Prérequis

- Node.js 18+ ou Docker
- Variables d'environnement configurées

### Configuration (IMPORTANTE ⚠️)

**Le dashboard ne fonctionnera pas sans configuration préalable.**

1. **Créer le fichier de configuration:**
   ```bash
   cd dashboard
   cp .env.example .env
   ```

2. **Générer les secrets sécurisés:**
   ```bash
   # Générer JWT_SECRET
   openssl rand -hex 32

   # Générer BOT_API_KEY
   openssl rand -hex 32
   ```

3. **Éditer le fichier .env:**
   ```bash
   nano .env  # ou votre éditeur préféré
   ```

   **Variables OBLIGATOIRES:**
   ```env
   # Authentification Dashboard
   JWT_SECRET=<votre_secret_jwt_généré>
   DASHBOARD_USER=<votre_nom_utilisateur>
   DASHBOARD_PASSWORD=<votre_mot_de_passe>

   # API Backend
   BOT_API_KEY=<votre_clé_api_générée>
   BOT_API_URL=http://api:8000  # ou http://localhost:8000 en dev
   ```

4. **Démarrer le dashboard:**

   **Avec Docker (recommandé):**
   ```bash
   docker-compose up -d
   ```

   **Ou en développement:**
   ```bash
   npm install
   npm run dev
   ```

5. **Accéder au dashboard:**
   - Ouvrir: http://localhost:3000
   - Se connecter avec `DASHBOARD_USER` et `DASHBOARD_PASSWORD`

## ❌ Résolution des problèmes courants

### "Erreur de connexion au serveur" lors du login

**Cause:** Les variables d'environnement ne sont pas configurées.

**Solution:**
1. Vérifier que le fichier `.env` existe
2. Vérifier que toutes les variables requises sont définies:
   - `JWT_SECRET` (minimum 32 caractères)
   - `DASHBOARD_USER`
   - `DASHBOARD_PASSWORD`
   - `BOT_API_KEY`

3. Redémarrer le dashboard après avoir modifié `.env`

### "Identifiants incorrects"

**Cause:** Le nom d'utilisateur ou mot de passe ne correspond pas à `.env`

**Solution:**
- Vérifier les valeurs de `DASHBOARD_USER` et `DASHBOARD_PASSWORD` dans `.env`
- S'assurer d'utiliser exactement les mêmes valeurs (sensible à la casse)

### Dashboard ne démarre pas avec Docker

**Solution:**
```bash
# Vérifier les logs
docker-compose logs app

# Reconstruire l'image
docker-compose build --no-cache
docker-compose up -d
```

## 📁 Structure du Projet

```
dashboard/
├── app/                    # Pages et routes Next.js
│   ├── api/               # API Routes
│   │   └── auth/          # Authentification endpoints
│   ├── login/             # Page de connexion
│   └── ...                # Autres pages
├── components/            # Composants React
├── lib/                   # Bibliothèques et utilitaires
│   ├── auth.ts           # Logique d'authentification JWT
│   └── api.ts            # Client API
├── .env.example          # Template de configuration
└── docker-compose.yml    # Configuration Docker

```

## 🔐 Sécurité

- **Ne jamais commiter le fichier `.env`** (il est dans `.gitignore`)
- Utiliser des secrets forts générés aléatoirement
- Changer les mots de passe par défaut
- En production, activer `SECURE_COOKIES=true`
- Utiliser HTTPS en production

## 🛠️ Développement

```bash
# Installer les dépendances
npm install

# Développement avec hot-reload
npm run dev

# Build pour production
npm run build

# Démarrer en production
npm start

# Linting
npm run lint
```

## 📚 Documentation

### Authentification

Le dashboard utilise un système d'authentification à deux niveaux:

1. **Authentification Dashboard:** Login avec username/password (JWT tokens)
2. **Authentification LinkedIn:** Gestion de la session LinkedIn du bot

### Variables d'Environnement

Voir `.env.example` pour la liste complète des variables disponibles.

### API Endpoints

- `POST /api/auth/login` - Connexion au dashboard
- `POST /api/auth/logout` - Déconnexion
- `GET /api/bot/status` - Statut du bot
- Et plus encore...

## 🐛 Support

En cas de problème:

1. Vérifier les logs: `docker-compose logs -f app`
2. Vérifier la configuration `.env`
3. Consulter la documentation du projet principal
4. Créer une issue sur GitHub

## 📝 License

Ce projet fait partie de LinkedIn Birthday Auto Bot.
