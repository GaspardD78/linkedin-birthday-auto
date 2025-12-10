# Guide de réparation Nginx

## 🔧 Vue d'ensemble

Le script `fix_nginx.sh` est un outil de réparation automatique qui installe et configure Nginx avec toutes les protections de sécurité requises pour le LinkedIn Birthday Bot.

## ⚠️ Quand utiliser ce script ?

Utilisez ce script si vous rencontrez l'un des problèmes suivants :

- ✗ Nginx n'est pas installé
- ✗ Nginx ne démarre pas
- ✗ Erreur: `limit_req_zone directive is not allowed here`
- ✗ Configuration Nginx invalide
- ✗ Zones de rate limiting manquantes
- ✗ Configuration linkedin-bot manquante

## 🚀 Utilisation

### Installation et configuration complète

```bash
./scripts/fix_nginx.sh
```

Le script va vous demander votre nom de domaine et procéder à l'installation complète.

### Ce que fait le script

Le script effectue les opérations suivantes dans l'ordre :

1. **Installation de Nginx** (si nécessaire)
   - Installe nginx via apt
   - Active le service au démarrage

2. **Création des répertoires**
   - `/etc/nginx/sites-available/`
   - `/etc/nginx/sites-enabled/`
   - `/etc/nginx/conf.d/`
   - `/var/www/html/`

3. **Configuration des zones de rate limiting**
   - Copie `rate-limit-zones.conf` dans `/etc/nginx/conf.d/`
   - Configure 3 zones de protection :
     - `general` : 10 requêtes/seconde max
     - `login` : 5 tentatives/15 minutes
     - `api` : 60 requêtes/minute

4. **Mise à jour de nginx.conf**
   - Ajoute l'inclusion des fichiers `.conf` depuis `/etc/nginx/conf.d/`
   - Nécessaire pour charger les zones de rate limiting

5. **Installation de la configuration linkedin-bot**
   - Copie `linkedin-bot.conf` dans `/etc/nginx/sites-available/`
   - Remplace `YOUR_DOMAIN.COM` par votre domaine
   - Active la configuration via un lien symbolique

6. **Installation des pages d'erreur**
   - Copie `429.html` (Too Many Requests) dans `/var/www/html/`

7. **Test et démarrage**
   - Teste la configuration avec `nginx -t`
   - Démarre ou recharge Nginx
   - Active Nginx au démarrage du système

## 📋 Prérequis

- Système Ubuntu/Debian
- Accès sudo
- Fichiers de configuration dans `deployment/nginx/`
- Ports 80 et 443 disponibles

## 🔐 Sécurité

### Backups automatiques

Le script crée des backups avant toute modification :

```
/etc/nginx/conf.d/rate-limit-zones.conf.backup.YYYYMMDD_HHMMSS
/etc/nginx/sites-available/linkedin-bot.backup.YYYYMMDD_HHMMSS
```

### Protections installées

Le script configure les protections de sécurité suivantes :

#### Headers de sécurité

- **HSTS** : Force HTTPS pendant 1 an
- **X-Frame-Options** : Protection contre le clickjacking
- **X-Content-Type-Options** : Désactive le MIME sniffing
- **X-XSS-Protection** : Protection XSS du navigateur
- **Content-Security-Policy** : Politique de sécurité du contenu
- **X-Robots-Tag** : Anti-indexation moteurs de recherche

#### Rate Limiting

- **General** : 10 req/s par IP (burst: 20)
- **Login** : 5 tentatives/15 min (burst: 2)
- **API** : 60 req/min (burst: 10)

#### Autres protections

- Blocage des fichiers sensibles (`.env`, `.git`)
- Blocage des fichiers de backup (`~`)
- Logs séparés pour les tentatives de login
- Timeouts appropriés pour les opérations bot

## 📝 Exemple de sortie

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  🔧 Réparation et installation de Nginx
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[1/7] Vérification de Nginx...
Installation de Nginx...
✓ Nginx installé

[2/7] Création des répertoires...
✓ Répertoires créés

[3/7] Configuration des zones de rate limiting...
✓ Zones de rate limiting configurées

[4/7] Vérification de nginx.conf...
✓ Inclusion déjà présente

[5/7] Installation de la configuration linkedin-bot...
Veuillez entrer votre nom de domaine (ex: gaspardanoukolivier.freeboxos.fr)
Domaine: votre-domaine.com
✓ Configuration installée pour le domaine: votre-domaine.com

[6/7] Activation de la configuration...
✓ Configuration activée

[7/7] Installation des pages d'erreur...
✓ Page 429.html installée

Test de la configuration Nginx...
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

✓ Configuration Nginx valide

Démarrage de Nginx...
✓ Nginx démarré avec succès

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ✓ Installation et configuration réussies !
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Prochaines étapes:
  1. Vérifiez que votre DNS pointe vers ce serveur
  2. Obtenez un certificat SSL avec: sudo certbot --nginx -d votre-domaine.com
  3. Relancez le script de vérification: ./scripts/verify_security.sh
```

## 🔄 Workflow après installation

### 1. Vérifier que Nginx fonctionne

```bash
sudo systemctl status nginx
curl -I http://localhost
```

### 2. Configurer DNS

Assurez-vous que votre domaine pointe vers l'IP de votre serveur :

```bash
dig votre-domaine.com
```

### 3. Obtenir un certificat SSL

```bash
sudo certbot --nginx -d votre-domaine.com
```

Certbot va :
- Obtenir un certificat Let's Encrypt
- Modifier automatiquement la configuration Nginx
- Activer HTTPS
- Configurer le renouvellement automatique

### 4. Vérifier la sécurité

```bash
./scripts/verify_security.sh
```

Le score de sécurité devrait maintenant être bien meilleur !

### 5. Tester en production

```bash
# Tester l'accès HTTPS
curl -I https://votre-domaine.com

# Vérifier les headers de sécurité
curl -I https://votre-domaine.com | grep -i "x-frame\|hsts\|content-type"

# Tester le rate limiting (devrait retourner 429 après plusieurs requêtes)
for i in {1..25}; do curl -I http://localhost; done
```

## 🆘 Dépannage

### Nginx ne démarre pas

```bash
# Vérifier les logs
sudo journalctl -xeu nginx

# Vérifier la configuration
sudo nginx -t

# Vérifier les ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
```

### Erreur "port already in use"

Un autre service utilise les ports 80 ou 443 :

```bash
# Identifier le processus
sudo lsof -i :80
sudo lsof -i :443

# Arrêter le service concurrent (exemple avec Apache)
sudo systemctl stop apache2
sudo systemctl disable apache2
```

### Erreur de permission

```bash
# Vérifier les permissions
ls -la /etc/nginx/sites-available/linkedin-bot
ls -la /var/www/html/429.html

# Corriger si nécessaire
sudo chmod 644 /etc/nginx/sites-available/linkedin-bot
sudo chmod 644 /var/www/html/429.html
```

### Erreur: invalid rate "rate=5r/15m"

Cette erreur se produit avec une ancienne version du fichier `rate-limit-zones.conf` qui utilise une syntaxe invalide pour Nginx.

**Problème** : Nginx n'accepte que `r/s` (par seconde) ou `r/m` (par minute), pas `r/15m` (par 15 minutes).

**Solution rapide** :

```bash
# Script de correction automatique
./scripts/fix_nginx_ratelimit.sh
```

**Solution manuelle** :

```bash
# 1. Sauvegarder l'ancien fichier
sudo cp /etc/nginx/conf.d/rate-limit-zones.conf /etc/nginx/conf.d/rate-limit-zones.conf.backup

# 2. Copier le fichier corrigé depuis le projet
sudo cp deployment/nginx/rate-limit-zones.conf /etc/nginx/conf.d/

# 3. Tester la configuration
sudo nginx -t

# 4. Recharger Nginx
sudo systemctl reload nginx
```

**Note technique** : La zone de login passe de `rate=5r/15m` (invalide) à `rate=1r/m` avec `burst=5`, permettant ~5 tentatives par 5 minutes. C'est la meilleure approximation possible avec les limitations de Nginx.

### Zones de rate limiting toujours manquantes

Vérifiez manuellement :

```bash
# Voir si le fichier existe
cat /etc/nginx/conf.d/rate-limit-zones.conf

# Vérifier qu'il est inclus
sudo grep -r "include.*conf.d" /etc/nginx/nginx.conf

# Ajouter manuellement si nécessaire
sudo nano /etc/nginx/nginx.conf
# Ajoutez dans le bloc http {} :
#     include /etc/nginx/conf.d/*.conf;
```

### Le domaine ne fonctionne pas

1. Vérifiez que le DNS est configuré :
   ```bash
   nslookup votre-domaine.com
   ping votre-domaine.com
   ```

2. Vérifiez que le domaine est dans la config :
   ```bash
   sudo grep "server_name" /etc/nginx/sites-available/linkedin-bot
   ```

3. Relancez le script avec le bon domaine :
   ```bash
   ./scripts/fix_nginx.sh
   ```

## 📚 Fichiers de configuration

### Structure après installation

```
/etc/nginx/
├── nginx.conf                              # Config principale
├── conf.d/
│   └── rate-limit-zones.conf              # Zones de rate limiting
├── sites-available/
│   └── linkedin-bot                       # Config du bot
└── sites-enabled/
    └── linkedin-bot -> ../sites-available/linkedin-bot

/var/www/html/
└── 429.html                               # Page d'erreur rate limit
```

### Modification de la configuration

Pour modifier la configuration après installation :

```bash
# Éditer la config
sudo nano /etc/nginx/sites-available/linkedin-bot

# Tester
sudo nginx -t

# Recharger
sudo systemctl reload nginx
```

## 🔗 Ressources complémentaires

- **Script de vérification** : `./scripts/verify_security.sh`
- **Guide de vérification** : `docs/VERIFY_SECURITY_GUIDE.md`
- **Configuration Nginx** : `deployment/nginx/linkedin-bot.conf`
- **Documentation Nginx** : https://nginx.org/en/docs/

## 💡 Intégration avec verify_security.sh

Le script `verify_security.sh` détecte automatiquement les problèmes Nginx et suggère d'utiliser `fix_nginx.sh` :

```bash
# Lancer la vérification
./scripts/verify_security.sh

# Si des problèmes Nginx sont détectés, suivre les recommandations :
#   → ./scripts/fix_nginx.sh

# Relancer la vérification pour confirmer
./scripts/verify_security.sh
```

## ⚙️ Configuration avancée

### Personnaliser les limites de rate limiting

Éditez `/etc/nginx/conf.d/rate-limit-zones.conf` :

```nginx
# Exemple : augmenter le rate limit API
limit_req_zone $binary_remote_addr zone=api:10m rate=100r/m;
```

### Ajouter des domaines

Pour servir plusieurs domaines :

```bash
# Copier la config
sudo cp /etc/nginx/sites-available/linkedin-bot /etc/nginx/sites-available/linkedin-bot-2

# Éditer et changer le domaine
sudo nano /etc/nginx/sites-available/linkedin-bot-2

# Activer
sudo ln -s /etc/nginx/sites-available/linkedin-bot-2 /etc/nginx/sites-enabled/

# Tester et recharger
sudo nginx -t && sudo systemctl reload nginx
```

### Configurer les logs

Les logs sont dans `/var/log/nginx/` :

- `linkedin-bot-access.log` : Accès normaux
- `linkedin-bot-error.log` : Erreurs
- `linkedin-bot-ratelimit.log` : Tentatives de rate limiting
- `linkedin-bot-login.log` : Tentatives de login

```bash
# Voir les logs en temps réel
sudo tail -f /var/log/nginx/linkedin-bot-access.log

# Analyser les rate limits
sudo grep "429" /var/log/nginx/linkedin-bot-ratelimit.log
```
