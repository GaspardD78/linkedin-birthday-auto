# 🔐 Récupération et Modification du Mot de Passe Dashboard

## Identifiants actuels

**Connexion au dashboard** (`http://IP_RASPBERRY:3000`) :
- **Utilisateur** : `admin`
- **Mot de passe** : `LinkedinBot2024!`

> ⚠️ **Important** : Utilisez le mot de passe EN CLAIR pour vous connecter, PAS le hash bcrypt du fichier `.env`

---

## Changer votre mot de passe

### Méthode 1 : Script automatique (Recommandée)

```bash
./scripts/init_env.sh
```

Ce script va :
1. Sauvegarder votre `.env` actuel
2. Vous demander un nouveau mot de passe
3. Le hasher automatiquement avec bcrypt
4. Mettre à jour le `.env`

### Méthode 2 : Manuelle

#### Étape 1 : Générer le hash bcrypt

```bash
node dashboard/scripts/hash_password.js "VotreNouveauMotDePasse"
```

Cela affichera quelque chose comme :
```
✅ Mot de passe hashé avec succès!

Copiez cette ligne dans votre fichier .env:
─────────────────────────────────────────────────
DASHBOARD_PASSWORD=$2b$12$AbCdEf...
─────────────────────────────────────────────────
```

#### Étape 2 : Copier le hash

Copiez le hash complet (commence par `$2b$12$` ou `$2a$12$`)

#### Étape 3 : Modifier le .env

```bash
nano .env
```

Remplacez la ligne `DASHBOARD_PASSWORD=...` par le nouveau hash :
```bash
DASHBOARD_PASSWORD=$2b$12$VotreNouveauHash...
```

#### Étape 4 : Redémarrer le dashboard

```bash
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

#### Étape 5 : Vérifier les logs

```bash
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard
```

---

## Diagnostic : Mot de passe ne fonctionne pas

### Vérifier la configuration actuelle

```bash
./scripts/diagnose_password.sh
```

Ce script vérifie :
- ✅ Le fichier `.env` existe
- ✅ La variable `DASHBOARD_PASSWORD` est présente
- ✅ Le mot de passe est au format bcrypt
- ✅ La longueur du hash est correcte (60 caractères)

### Problèmes courants

#### 1. "Impossible de se connecter"

**Cause** : Le dashboard n'a pas été redémarré après modification du `.env`

**Solution** :
```bash
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

#### 2. "Identifiants incorrects"

**Vérifications** :
- ✅ Utilisez le mot de passe **en clair**, pas le hash du `.env`
- ✅ Vérifiez qu'il n'y a pas d'espaces avant/après le mot de passe
- ✅ Vérifiez le nom d'utilisateur (défaut : `admin`)
- ✅ **Vérifiez que le hash contient `$$` et non `$`** dans le `.env`

**Problème fréquent** : Si vous avez copié un hash avec des `$` simples au lieu de `$$`, Docker Compose interprétera les `$` comme des variables vides.

**Solution** : Régénérez le hash avec le script :
```bash
node dashboard/scripts/hash_password.js "VotreMotDePasse"
# Le script génère automatiquement avec $$
# Copiez le hash dans .env
# Redémarrez le dashboard
```

#### 3. "Le mot de passe en clair ne fonctionne pas"

**Cause** : Le hash dans le `.env` ne correspond pas au mot de passe que vous utilisez

**Solution** : Réinitialisez avec le script :
```bash
./scripts/init_env.sh
```

---

## Variables d'environnement dashboard

Dans le fichier `.env`, ces variables sont requises pour l'authentification :

```bash
# JWT pour les sessions (généré automatiquement)
JWT_SECRET=...

# Identifiants de connexion
DASHBOARD_USER=admin
DASHBOARD_PASSWORD=$2a$12$...  # Hash bcrypt, PAS le mot de passe en clair
```

---

## Sécurité

### ✅ Bonnes pratiques

1. **Toujours hasher** : Le mot de passe dans `.env` doit TOUJOURS être un hash bcrypt
2. **Mot de passe fort** : Minimum 12 caractères avec lettres, chiffres et symboles
3. **Gestionnaire de mots de passe** : Conservez votre mot de passe dans 1Password, Bitwarden, etc.
4. **Ne jamais commiter** : Le fichier `.env` est dans `.gitignore` pour éviter les fuites

### ⚠️ À éviter

- ❌ Stocker le mot de passe en clair dans `.env`
- ❌ Commiter le fichier `.env` dans git
- ❌ Utiliser des mots de passe faibles (< 8 caractères)
- ❌ Partager votre mot de passe par email/chat

---

## Format bcrypt

Un hash bcrypt valide dans le fichier `.env` ressemble à :
```
$$2a$$12$$qLt6w0u7xkKbJB19gLP3r.E8DtHyNsuslKPOBtvHnl7f4apyR539W
```

⚠️ **Important** : Notez les `$$` (double dollar) au lieu de `$` !

### Pourquoi les `$$` ?

Docker Compose interprète les `$` comme des variables d'environnement. Pour utiliser un `$` littéral dans un fichier `.env`, il faut le doubler : `$$`.

**Exemple** :
- Hash bcrypt original : `$2a$12$abc...`
- Dans `.env` pour Docker Compose : `$$2a$$12$$abc...`

Le script `hash_password.js` génère automatiquement le hash avec les `$$` doublés.

### Structure du hash :
- `$$2a$$` ou `$$2b$$` : Version de l'algorithme (échappée pour Docker)
- `12` : Nombre de rounds (12 = recommandé, équilibre sécurité/performance)
- Le reste : Salt + hash (60 caractères au total avec les `$` doublés)

---

## Commandes utiles

```bash
# Redémarrer uniquement le dashboard
docker compose -f docker-compose.pi4-standalone.yml restart dashboard

# Voir les logs en temps réel
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard

# Vérifier que le dashboard tourne
docker compose -f docker-compose.pi4-standalone.yml ps dashboard

# Voir l'état de santé
docker compose -f docker-compose.pi4-standalone.yml ps

# Diagnostiquer le mot de passe
./scripts/diagnose_password.sh

# Générer un nouveau hash
node dashboard/scripts/hash_password.js "VotreMotDePasse"
```

---

## Support

Si vous rencontrez des problèmes :

1. Exécutez le diagnostic : `./scripts/diagnose_password.sh`
2. Vérifiez les logs : `docker compose -f docker-compose.pi4-standalone.yml logs dashboard`
3. Consultez la documentation : `docs/`
4. Ouvrez une issue sur GitHub avec les logs

---

**Dernière mise à jour** : 2025-12-10
