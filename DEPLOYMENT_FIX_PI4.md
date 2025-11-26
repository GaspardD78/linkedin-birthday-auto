# 🔧 Correctifs Critiques - Déploiement Pi4 (Session 01VFQLWTfWbzvZev2RgqZvHs)

## 📋 Résumé des problèmes corrigés

### ❌ Problème initial
Le conteneur `linkedin-dashboard` plantait avec l'erreur :
```
TypeError: Failed to parse URL from undefined/auth/start
```

**Cause racine** : Les variables d'environnement Docker (`BOT_API_URL`) n'étaient pas accessibles dans les API routes Next.js au moment du runtime, car Next.js ne les exposait pas explicitement.

---

## ✅ Corrections appliquées

### 1. **Configuration Next.js** (`dashboard/next.config.js`)
**Changement** : Ajout de la propriété `env` pour exposer les variables d'environnement au runtime serveur.

```javascript
env: {
  BOT_API_URL: process.env.BOT_API_URL || 'http://linkedin-bot-api:8000',
  BOT_API_KEY: process.env.BOT_API_KEY || 'internal_secret_key',
  BOT_REDIS_HOST: process.env.BOT_REDIS_HOST || 'redis-bot',
  BOT_REDIS_PORT: process.env.BOT_REDIS_PORT || '6379',
  BOT_REDIS_URL: process.env.BOT_REDIS_URL || 'redis://redis-bot:6379',
}
```

**Impact** : Les variables définies dans `docker-compose.pi4-standalone.yml` sont maintenant accessibles dans toutes les API routes.

---

### 2. **Routes API avec fallback incorrect** (3 fichiers)
**Fichiers modifiés** :
- `dashboard/app/api/auth/start/route.ts:8`
- `dashboard/app/api/auth/verify-2fa/route.ts:8`
- `dashboard/app/api/auth/upload/route.ts:6`

**Avant** :
```typescript
const apiUrl = process.env.BOT_API_URL || 'http://api:8000';  // ❌ Mauvais nom
```

**Après** :
```typescript
const apiUrl = process.env.BOT_API_URL || 'http://linkedin-bot-api:8000';  // ✅ Correct
```

**Impact** : Même si la variable d'env est `undefined`, le fallback pointe vers le bon conteneur Docker.

---

### 3. **Gestion d'erreurs UI visible** (2 composants)

#### A. `dashboard/components/dashboard/StatsWidget.tsx`
**Ajout** : Affichage d'une carte d'erreur rouge si l'API est inaccessible.

**Avant** : Erreur silencieuse dans la console uniquement.

**Après** : Card rouge visible avec le message d'erreur et instructions de diagnostic.

#### B. `dashboard/components/dashboard/HealthWidget.tsx`
**Ajout** : Affichage d'une carte d'erreur jaune si le health check échoue.

---

### 4. **Route API Stats transparente** (`dashboard/app/api/stats/route.ts`)
**Changement** : Retour d'un statut HTTP d'erreur approprié au lieu de toujours retourner 200 avec des valeurs à 0.

**Avant** :
```typescript
if (!response.ok) {
  return NextResponse.json({ wishes_sent_total: 0, ... });  // Status 200
}
```

**Après** :
```typescript
if (!response.ok) {
  return NextResponse.json(
    { error: 'Bot API unreachable', detail: `...` },
    { status: 503 }  // Service Unavailable
  );
}
```

**Impact** : Le frontend peut maintenant détecter les erreurs API et afficher un message à l'utilisateur.

---

### 5. **Propagation d'erreurs dans `lib/api.ts`**
**Changement** : La fonction `getBotStats()` ne masque plus les erreurs avec des valeurs par défaut.

**Avant** : Retournait `{ wishes_sent_total: 0, ... }` en cas d'erreur.

**Après** : Lance une exception qui remonte au composant UI pour affichage.

---

### 6. **Scripts de redémarrage** (2 nouveaux scripts)

#### A. `scripts/rebuild-dashboard-pi4.sh`
- Arrête le conteneur dashboard
- Force une reconstruction **sans cache**
- Redémarre le dashboard uniquement
- Durée : ~10-15 min sur Pi4

#### B. `scripts/restart-all-pi4.sh`
- Arrête **tous** les services
- Reconstruction complète sans cache
- Redémarre toute l'architecture
- Durée : ~15-20 min sur Pi4

Les deux scripts sont marqués exécutables (`chmod +x`).

---

## 🚀 Instructions de déploiement sur Raspberry Pi 4

### Option 1 : Reconstruction dashboard uniquement (recommandée)
```bash
cd /path/to/linkedin-birthday-auto
./scripts/rebuild-dashboard-pi4.sh
```

### Option 2 : Reconstruction complète (si problèmes persistants)
```bash
cd /path/to/linkedin-birthday-auto
./scripts/restart-all-pi4.sh
```

### Option 3 : Commandes manuelles (avancé)
```bash
# Arrêter le dashboard
docker compose -f docker-compose.pi4-standalone.yml stop dashboard

# Supprimer le conteneur
docker compose -f docker-compose.pi4-standalone.yml rm -f dashboard

# Rebuild sans cache (CRITIQUE)
docker compose -f docker-compose.pi4-standalone.yml build --no-cache dashboard

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml up -d dashboard

# Vérifier les logs
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard
```

---

## 🔍 Vérification post-déploiement

1. **Vérifier que tous les conteneurs sont UP** :
   ```bash
   docker compose -f docker-compose.pi4-standalone.yml ps
   ```

2. **Tester l'URL du dashboard** :
   ```bash
   curl http://localhost:3000/api/system/health
   ```

3. **Vérifier les logs du dashboard** :
   ```bash
   docker compose -f docker-compose.pi4-standalone.yml logs --tail=50 dashboard
   ```

4. **Tester l'authentification** (depuis le navigateur) :
   - Accéder à `http://<raspberry-pi-ip>:3000`
   - Cliquer sur "Start Authentication"
   - Vérifier qu'il n'y a plus d'erreur "Failed to parse URL from undefined"

---

## 🎯 Améliorations préventives appliquées

1. ✅ **Cohérence des noms Docker** : Tous les fallbacks pointent vers `linkedin-bot-api` (nom correct du conteneur).
2. ✅ **Gestion d'erreurs visible** : Les erreurs API sont maintenant affichées à l'utilisateur, pas seulement dans la console.
3. ✅ **Propagation d'erreurs transparente** : Les routes API retournent des codes d'erreur HTTP appropriés.
4. ✅ **Scripts automatisés** : Facilite le redémarrage propre après modifications.

---

## 📝 Notes importantes

- **Durée du rebuild** : Le build Next.js standalone sur Pi4 prend 10-15 minutes. C'est normal.
- **Cache Docker** : Le flag `--no-cache` est **critique** pour forcer l'utilisation des nouvelles variables d'env.
- **Test avant production** : Après le rebuild, testez d'abord en local avant de lancer le bot en production.

---

## 📊 Fichiers modifiés (résumé)

```
Modifiés :
  ✅ dashboard/next.config.js
  ✅ dashboard/app/api/auth/start/route.ts
  ✅ dashboard/app/api/auth/verify-2fa/route.ts
  ✅ dashboard/app/api/auth/upload/route.ts
  ✅ dashboard/app/api/stats/route.ts
  ✅ dashboard/components/dashboard/StatsWidget.tsx
  ✅ dashboard/components/dashboard/HealthWidget.tsx
  ✅ dashboard/lib/api.ts

Créés :
  ✅ scripts/rebuild-dashboard-pi4.sh
  ✅ scripts/restart-all-pi4.sh
  ✅ DEPLOYMENT_FIX_PI4.md (ce fichier)
```

---

## 🛡️ Prévention de régression

Pour éviter que ce problème ne se reproduise :

1. **Toujours définir les variables d'env dans `next.config.js`** si elles doivent être accessibles au runtime.
2. **Tester le rebuild sans cache** après toute modification de configuration.
3. **Utiliser les scripts fournis** plutôt que des commandes manuelles.
4. **Vérifier les logs** après chaque déploiement pour détecter rapidement les erreurs.

---

**Auteur** : Claude Code (Session 01VFQLWTfWbzvZev2RgqZvHs)
**Date** : 2025-11-26
**Branche** : `claude/deploy-birthday-bot-pi4-01VFQLWTfWbzvZev2RgqZvHs`
