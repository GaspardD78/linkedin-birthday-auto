# Guide d'utilisation du script de vérification de sécurité

## 🔍 Vue d'ensemble

Le script `verify_security.sh` (version 2.0) teste toutes les protections de sécurité de votre bot LinkedIn Birthday et peut maintenant **réparer automatiquement** les problèmes détectés.

## 📋 Utilisation

### Mode vérification simple

```bash
./scripts/verify_security.sh
```

Ce mode effectue tous les tests de sécurité et affiche les résultats. À la fin, si des problèmes sont détectés, le script vous demandera si vous souhaitez les réparer.

### Mode réparation automatique

```bash
./scripts/verify_security.sh --fix
```

Ou avec l'option courte :

```bash
./scripts/verify_security.sh -f
```

Ce mode effectue les tests ET répare automatiquement tous les problèmes détectés sans demander de confirmation.

## 🔧 Problèmes réparables automatiquement

Le script peut réparer automatiquement les problèmes suivants :

### 1. Base de données manquante
- **Problème** : Le fichier `data/linkedin_bot.db` n'existe pas
- **Réparation** : Crée le répertoire `data/` et initialise une base SQLite vide avec la table `contacts`

### 2. Nginx non actif
- **Problème** : Le service Nginx n'est pas démarré, ou pas installé, ou mal configuré
- **Réparation** :
  - Vérifie l'installation de Nginx
  - Vérifie la présence des zones de rate limiting
  - Teste la configuration
  - Démarre Nginx avec `sudo systemctl start nginx`
  - Si des erreurs critiques sont détectées, suggère d'utiliser `./scripts/fix_nginx.sh`

### 3. Configuration Nginx invalide
- **Problème** : La configuration Nginx contient des erreurs (notamment zones de rate limiting manquantes)
- **Réparation** :
  - Diagnostique les erreurs de configuration
  - Vérifie la présence des zones de rate limiting
  - Suggère d'utiliser `./scripts/fix_nginx.sh` pour une réparation complète
  - Recharge Nginx si la configuration devient valide

### 4. Mot de passe en clair
- **Problème** : Le mot de passe dans `.env` n'est pas hashé avec bcrypt
- **Réparation** :
  - Crée un backup du fichier `.env`
  - Hash le mot de passe avec bcrypt
  - Met à jour le fichier `.env`

### 5. Permissions .env incorrectes
- **Problème** : Le fichier `.env` n'a pas les permissions restrictives (600)
- **Réparation** : Applique `chmod 600 .env`

### 6. Security headers manquants
- **Problème** : Les headers de sécurité ne sont pas configurés dans Nginx
- **Réparation** : Ajoute automatiquement les headers suivants :
  - `X-Frame-Options: DENY`
  - `X-Content-Type-Options: nosniff`
  - `X-Robots-Tag: noindex, nofollow`
  - `Strict-Transport-Security: max-age=31536000`

### 7. Meta tags robots incomplets
- **Problème** : Les meta tags anti-indexation manquent dans `layout.tsx`
- **Réparation** : Ajoute les meta tags `robots` appropriés dans le fichier

## 📊 Exemple de sortie

### Après vérification

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  📊 RÉSUMÉ DES TESTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RÉSULTATS :
  ✓ Tests réussis     : 24
  ✗ Tests échoués     : 4
  ⚠ Avertissements    : 8
  ━ Total             : 37

SCORE SÉCURITÉ :
  ❌ 64.8% - INSUFFISANT
  Action requise pour sécuriser votre bot !
```

### Réparation interactive

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔧 RÉPARATION AUTOMATIQUE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

5 problème(s) peuvent être réparés automatiquement

Voulez-vous réparer ces problèmes maintenant ?

Répondre (o/n) : o

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Réparation: Base de données manquante

Création de la base de données...
Base de données créée avec succès
✓ Réparation réussie
```

## 🔄 Workflow recommandé

1. **Première vérification** :
   ```bash
   ./scripts/verify_security.sh
   ```

2. **Réparer les problèmes** :
   - Mode interactif : répondez "o" à la question
   - Ou mode automatique : `./scripts/verify_security.sh --fix`

3. **Vérifier à nouveau** :
   ```bash
   ./scripts/verify_security.sh
   ```
   Le score de sécurité devrait maintenant être plus élevé

4. **Itérer si nécessaire** : Répétez les étapes 2-3 jusqu'à obtenir un score satisfaisant (> 90%)

## ⚠️ Précautions

### Backups automatiques

Le script crée automatiquement des backups avant toute modification :

- **Fichier .env** : `.env.backup.YYYYMMDD_HHMMSS`
- **Configuration Nginx** : `/etc/nginx/sites-available/linkedin-bot.backup.YYYYMMDD_HHMMSS`
- **Fichier layout.tsx** : `dashboard/app/layout.tsx.backup.YYYYMMDD_HHMMSS`

### Permissions requises

Certaines réparations nécessitent des privilèges sudo :
- Démarrage de Nginx
- Modification de la configuration Nginx
- Rechargement de Nginx

Le script demandera votre mot de passe sudo si nécessaire.

### Réparations qui peuvent échouer

Certaines réparations peuvent échouer dans les cas suivants :

1. **Mot de passe hashé** : Si le script `hash_password.js` n'existe pas ou si node n'est pas installé
2. **Nginx** : Si les fichiers de configuration sont corrompus ou mal formatés
3. **Base de données** : Si Python3 n'est pas installé ou si les permissions sont insuffisantes

## 🆘 Dépannage

### Le script ne trouve pas les fonctions de réparation

Assurez-vous d'exécuter le script depuis la racine du projet :

```bash
cd /path/to/linkedin-birthday-auto
./scripts/verify_security.sh
```

### Les réparations échouent

1. Vérifiez les logs d'erreur affichés
2. Vérifiez que tous les prérequis sont installés (node, python3, nginx, etc.)
3. Vérifiez les permissions de vos fichiers
4. Consultez les backups créés en cas de problème

### Problèmes Nginx spécifiques

Si les réparations Nginx échouent :

1. **Nginx pas installé** : Le script suggère d'utiliser `./scripts/fix_nginx.sh`
2. **Zones de rate limiting manquantes** : Utilisez `./scripts/fix_nginx.sh` pour une installation complète
3. **Erreur "limit_req_zone not allowed here"** : C'est un problème de configuration, utilisez `./scripts/fix_nginx.sh`

Consultez le guide complet : `docs/FIX_NGINX_GUIDE.md`

### Le score ne s'améliore pas

Certains problèmes nécessitent une intervention manuelle :
- Installation de rclone
- Configuration de Google Drive
- Obtention d'un certificat SSL
- Configuration DNS

Consultez le guide `SECURITY_SETUP_GUIDE.md` pour ces étapes.

## 📚 Ressources complémentaires

- **Installation complète** : `./scripts/setup_security.sh`
- **Réparation Nginx** : `./scripts/fix_nginx.sh` (voir `docs/FIX_NGINX_GUIDE.md`)
- **Guide de sécurité** : `docs/SECURITY_SETUP_GUIDE.md`
- **Guide anti-indexation** : `docs/ANTI_INDEXATION_GUIDE.md`

## 🔗 Intégration CI/CD

Vous pouvez intégrer ce script dans votre pipeline CI/CD :

```bash
# Dans votre .github/workflows/security.yml
- name: Vérification sécurité
  run: ./scripts/verify_security.sh --fix
```

Le script retourne :
- **Code 0** : Tous les tests passent, aucun problème
- **Code 1** : Des tests ont échoué ou des réparations ont échoué
