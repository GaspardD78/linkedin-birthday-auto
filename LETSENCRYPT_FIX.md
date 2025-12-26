# Fix: Let's Encrypt Error 403

## Problème Résolu

Lors de l'obtention du certificat Let's Encrypt, Certbot recevait une erreur 403 (Forbidden) :

```
Type:   unauthorized
Detail: Invalid response from http://gaspardanoukolivier.freeboxos.fr/.well-known/acme-challenge/...: 403
```

## Cause Racine

Le script `setup_letsencrypt.sh` ne créait pas explicitement le dossier `.well-known/acme-challenge/` avec les permissions appropriées avant d'appeler Certbot. Cela pouvait entraîner :

1. **Permissions incorrectes** : Le dossier n'avait pas les permissions `755` nécessaires
2. **Dossier non créé** : Certbot devait créer le dossier lui-même, ce qui pouvait échouer
3. **Aucune validation** : Pas de test pour vérifier que Nginx pouvait servir les fichiers ACME avant d'appeler Certbot

## Corrections Appliquées

### 1. Création Explicite du Dossier ACME avec Permissions (setup_letsencrypt.sh:146-150)

```bash
mkdir -p "$WEBROOT/.well-known/acme-challenge"
chown -R 1000:1000 "$CERT_ROOT"
chmod -R 755 "$CERT_ROOT"
chmod 755 "$WEBROOT/.well-known"
chmod 755 "$WEBROOT/.well-known/acme-challenge"
```

**Impact** : Le dossier est créé avec les bonnes permissions AVANT l'appel à Certbot.

### 2. Test de Validation Nginx ACME (setup_letsencrypt.sh:268-308)

Ajout d'un test automatique qui :
1. Crée un fichier de test dans `.well-known/acme-challenge/`
2. Vérifie que Nginx peut servir ce fichier via `curl http://localhost/.well-known/acme-challenge/test-nginx-access`
3. Échoue avec un message détaillé si le test ne passe pas
4. Nettoie le fichier de test si le test réussit

**Impact** : Détection précoce des problèmes de configuration Nginx AVANT d'appeler Certbot et de consommer les rate limits Let's Encrypt.

### 3. Exclusion de linkedin-bot.conf du Versioning (.gitignore)

Ajout de :
```gitignore
# Nginx & SSL (generated files, not version controlled)
certbot/
deployment/nginx/ssl-dhparams.pem
deployment/nginx/linkedin-bot.conf
deployment/nginx/linkedin-bot.conf.backup.*
```

**Impact** : Le fichier `linkedin-bot.conf` est généré dynamiquement par `setup.sh` selon le mode (LAN, ACME BOOTSTRAP, ou HTTPS) et ne devrait pas être versionné.

## Comment Tester

### Sur le Raspberry Pi, après avoir récupéré les modifications :

```bash
# 1. Récupérer les modifications
cd ~/linkedin-birthday-auto
git pull origin claude/auto-router-implementation-bcJx0

# 2. Relancer le setup complet (recommandé)
./setup.sh

# OU relancer uniquement l'obtention du certificat
sudo ./scripts/setup_letsencrypt.sh --force
```

### Validation du Fix

Le script va maintenant :

1. ✅ Créer le dossier `.well-known/acme-challenge/` avec permissions `755`
2. ✅ Créer un fichier de test et vérifier que Nginx peut le servir
3. ✅ Afficher `✓ Nginx peut servir les fichiers ACME challenge`
4. ✅ Procéder à l'appel à Certbot

Si le test échoue, le script affichera :
```
❌ Nginx ne peut PAS servir les fichiers ACME challenge

Diagnostic:
  1. Vérifier que Nginx utilise le template ACME BOOTSTRAP:
     head -5 /home/gaspard/linkedin-birthday-auto/deployment/nginx/linkedin-bot.conf

  2. Vérifier les logs Nginx:
     docker compose logs nginx | tail -20
  ...
```

## Problèmes Potentiels Restants

Si le problème persiste même avec ce fix, vérifiez :

### 1. Port 80 Bloqué par le FAI

Certains FAI bloquent le port 80. Vérifiez :

```bash
# Depuis le Raspberry Pi
curl http://localhost/.well-known/acme-challenge/test-nginx-access

# Depuis Internet (remplacez <VOTRE_IP> par votre IP publique)
curl http://gaspardanoukolivier.freeboxos.fr/.well-known/acme-challenge/test-nginx-access
```

**Solution** : Configurer la redirection de port 80 dans votre box Freebox.

### 2. Configuration Nginx Incorrecte

Vérifiez que Nginx utilise bien le template ACME BOOTSTRAP :

```bash
head -5 ~/linkedin-birthday-auto/deployment/nginx/linkedin-bot.conf
```

Vous devriez voir :
```
# MODE ACME BOOTSTRAP
```

Si vous voyez `MODE LAN`, relancez `./setup.sh`.

### 3. Rate Limit Let's Encrypt

Si vous avez déjà fait plusieurs tentatives, vous pourriez être rate-limité :
- **5 échecs par heure** par compte
- **50 certificats par semaine** par domaine

**Solution** : Attendez 1 heure avant de réessayer.

## Files Modifiés

- `scripts/setup_letsencrypt.sh` : Création du webroot + test de validation
- `.gitignore` : Exclusion des fichiers générés
- `deployment/nginx/linkedin-bot.conf` : Retiré du versioning Git
- `docs/LETSENCRYPT_403_FIX.md` : Documentation détaillée du problème
- `LETSENCRYPT_FIX.md` : Ce fichier (résumé)

## Prochaines Étapes

1. Tester le fix sur le Raspberry Pi
2. Vérifier que le certificat Let's Encrypt est obtenu avec succès
3. Vérifier que Nginx bascule automatiquement en mode HTTPS après obtention
4. Supprimer les scripts/fichiers temporaires (`scripts/fix_letsencrypt_403.sh`, `docs/LETSENCRYPT_403_FIX.md`)

## Référence

- Commit: (sera ajouté après commit)
- Branch: `claude/auto-router-implementation-bcJx0`
- Issue: Let's Encrypt 403 Error
