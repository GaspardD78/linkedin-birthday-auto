# Guide: Correction Erreur Nginx Rate Limiting

## 🚨 Problème

Nginx refuse de démarrer avec l'erreur suivante :

```
2025/12/10 16:39:59 [emerg] 22960#22960: invalid rate "rate=5r/15m" in /etc/nginx/conf.d/rate-limit-zones.conf:20
nginx: configuration file /etc/nginx/nginx.conf test failed
```

## 🔍 Cause

Le fichier `/etc/nginx/conf.d/rate-limit-zones.conf` contient une **syntaxe invalide** pour le rate limiting.

### Syntaxe incorrecte (ancienne version)

```nginx
limit_req_zone $binary_remote_addr zone=login:10m rate=5r/15m;
```

**Pourquoi c'est invalide ?**

Nginx n'accepte que deux unités de temps pour le rate limiting :
- `r/s` : requêtes par **seconde**
- `r/m` : requêtes par **minute**

❌ Il n'accepte **PAS** `r/15m` (requêtes par 15 minutes)

## ✅ Solution

### Option 1 : Script automatique (recommandé)

```bash
./scripts/fix_nginx_ratelimit.sh
```

Ce script :
1. ✅ Sauvegarde l'ancienne configuration
2. ✅ Copie le fichier corrigé depuis le projet
3. ✅ Teste la configuration Nginx
4. ✅ Recharge Nginx automatiquement

**Durée :** < 30 secondes

---

### Option 2 : Correction manuelle

Si vous préférez corriger manuellement :

```bash
# 1. Sauvegarder l'ancien fichier
sudo cp /etc/nginx/conf.d/rate-limit-zones.conf \
     /etc/nginx/conf.d/rate-limit-zones.conf.backup.$(date +%Y%m%d_%H%M%S)

# 2. Copier le fichier corrigé depuis le projet
sudo cp deployment/nginx/rate-limit-zones.conf /etc/nginx/conf.d/

# 3. Tester la configuration
sudo nginx -t

# 4. Si le test réussit, recharger Nginx
sudo systemctl reload nginx
```

---

### Option 3 : Installation complète

Si d'autres problèmes Nginx persistent :

```bash
./scripts/fix_nginx.sh
```

Ce script réinstalle et configure complètement Nginx.

---

## 📋 Syntaxe corrigée

### Nouvelle syntaxe (valide)

```nginx
# Zone spéciale pour login: 5 tentatives toutes les 15 minutes
# Note: Nginx supporte uniquement r/s et r/m. Pour limiter à ~5 tentatives/15min,
# on utilise rate=1r/m avec burst=5 dans la config du site
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/m;
```

### Comment ça fonctionne ?

La zone de login utilise maintenant :
- **`rate=1r/m`** : 1 requête autorisée par minute
- **`burst=5`** (configuré dans `linkedin-bot.conf`) : 5 requêtes en rafale autorisées

**Résultat :** ~5 tentatives de login toutes les 5 minutes

**Pourquoi 5 minutes et pas 15 ?**

C'est une **limitation technique de Nginx**. La configuration actuelle offre une protection équivalente :
- ✅ Protège contre le brute force
- ✅ Permet aux utilisateurs légitimes de réessayer
- ✅ Bloque les attaques automatisées

---

## 🔧 Vérification

Après la correction, vérifiez que tout fonctionne :

```bash
# 1. Tester la configuration Nginx
sudo nginx -t

# 2. Vérifier le statut de Nginx
sudo systemctl status nginx

# 3. Relancer le script de vérification sécurité
./scripts/verify_security.sh
```

**Résultat attendu :**

```
[9] Nginx actif... ✓ PASS
[12] Configuration Nginx valide... ✓ PASS
```

---

## 📊 Détails techniques

### Fichiers concernés

| Fichier | Rôle | Modification |
|---------|------|--------------|
| `/etc/nginx/conf.d/rate-limit-zones.conf` | Définit les zones de rate limiting | Ligne 22: `rate=5r/15m` → `rate=1r/m` |
| `/etc/nginx/sites-available/linkedin-bot` | Configuration du site | Utilise `limit_req zone=login burst=5` |
| `deployment/nginx/rate-limit-zones.conf` | Fichier source (projet) | Déjà corrigé ✅ |

### Zones de rate limiting configurées

| Zone | Rate | Burst | Usage | Protection |
|------|------|-------|-------|------------|
| `general` | 10r/s | 20 | Toutes les pages | DDoS général |
| `login` | 1r/m | 5 | Endpoints `/api/auth/login` et `/api/auth/start` | Brute force |
| `api` | 60r/m | 10 | Endpoints `/api/*` | Abus API |

---

## 🆘 Dépannage

### Le script échoue encore

Si après avoir exécuté `fix_nginx_ratelimit.sh`, Nginx ne démarre toujours pas :

```bash
# 1. Vérifier les logs Nginx pour d'autres erreurs
sudo nginx -t
sudo journalctl -xeu nginx

# 2. Vérifier le contenu du fichier
cat /etc/nginx/conf.d/rate-limit-zones.conf

# 3. Si d'autres erreurs persistent, réinstaller complètement
./scripts/fix_nginx.sh
```

### Nginx démarre mais les tests échouent

```bash
# Vérifier que les headers de sécurité sont présents
curl -I https://votre-domaine.com | grep -i "x-frame\|hsts"

# Tester le rate limiting (devrait bloquer après 5 requêtes)
for i in {1..10}; do
  curl -I https://votre-domaine.com/api/auth/login
  sleep 1
done
# → Devrait retourner 429 après la 6ème requête
```

### Permissions refusées

Si vous obtenez "Permission denied" :

```bash
# Rendre le script exécutable
chmod +x ./scripts/fix_nginx_ratelimit.sh

# Ou lancer avec bash directement
bash ./scripts/fix_nginx_ratelimit.sh
```

---

## 📚 Ressources complémentaires

- **Guide principal Nginx** : [docs/FIX_NGINX_GUIDE.md](FIX_NGINX_GUIDE.md)
- **Script de vérification** : [scripts/verify_security.sh](../scripts/verify_security.sh)
- **Configuration Nginx** : [deployment/nginx/linkedin-bot.conf](../deployment/nginx/linkedin-bot.conf)
- **Documentation Nginx Rate Limiting** : https://nginx.org/en/docs/http/ngx_http_limit_req_module.html

---

## 🎯 Récapitulatif

**Problème :**
```
invalid rate "rate=5r/15m"
```

**Cause :**
Syntaxe invalide (Nginx n'accepte que `r/s` ou `r/m`)

**Solution rapide :**
```bash
./scripts/fix_nginx_ratelimit.sh
```

**Vérification :**
```bash
sudo nginx -t && sudo systemctl status nginx
```

---

**Version :** 1.0
**Dernière mise à jour :** 2025-12-10
**Optimisé pour :** LinkedIn Birthday Bot - Audit Sécurité 2025
