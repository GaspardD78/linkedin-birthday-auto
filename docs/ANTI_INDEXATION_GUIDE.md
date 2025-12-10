# 🔒 Protection Anti-Indexation - Guide Complet

## Pourquoi c'est critique ?

Votre dashboard LinkedIn Bot est **privé** et contient des informations sensibles :
- Accès à votre compte LinkedIn via cookies
- Historique de vos messages
- Configuration de votre bot
- Statistiques d'utilisation

**Si Google indexe votre dashboard** :
- ❌ Votre URL apparaît dans les résultats de recherche
- ❌ Attaquants peuvent trouver votre dashboard facilement
- ❌ Risque d'exposition de données sensibles (screenshots Google)
- ❌ Surface d'attaque augmentée (brute-force ciblé)

---

## 🛡️ Protections Implémentées (Multi-couches)

Nous avons mis en place **4 couches de protection** indépendantes :

### Couche 1 : robots.txt ✅
**Fichier** : `dashboard/public/robots.txt`

**Fonction** : Demande poliment aux robots de ne pas indexer

**Efficacité** : ⭐⭐⭐ Moyenne (les robots malveillants l'ignorent)

**Exemple** :
```
User-agent: *
Disallow: /

User-agent: Googlebot
Disallow: /
```

**Vérification** :
```bash
curl https://VOTRE_DOMAINE.COM/robots.txt
```

### Couche 2 : Meta Tags Noindex ✅
**Fichier** : `dashboard/app/layout.tsx`

**Fonction** : Balises HTML demandant aux moteurs de ne pas indexer

**Efficacité** : ⭐⭐⭐⭐ Bonne (Google et Bing respectent)

**Code** :
```tsx
export const metadata: Metadata = {
  robots: {
    index: false,
    follow: false,
    nocache: true,
    googleBot: {
      index: false,
      noimageindex: true,
    },
  },
};
```

**Génère** :
```html
<meta name="robots" content="noindex, nofollow, nocache">
<meta name="googlebot" content="noindex, nofollow, noimageindex">
```

**Vérification** :
```bash
curl -s https://VOTRE_DOMAINE.COM | grep -i "robots"
```

### Couche 3 : Header HTTP X-Robots-Tag (Next.js) ✅
**Fichier** : `dashboard/next.config.js`

**Fonction** : Header HTTP envoyé à chaque requête

**Efficacité** : ⭐⭐⭐⭐⭐ Excellente (prioritaire sur meta tags)

**Header** :
```
X-Robots-Tag: noindex, nofollow, noarchive, nosnippet, noimageindex, nocache
```

**Signification** :
- `noindex` : Ne pas ajouter à l'index Google
- `nofollow` : Ne pas suivre les liens
- `noarchive` : Pas de cache Google (pas de "Version en cache")
- `nosnippet` : Pas d'extrait dans résultats
- `noimageindex` : Pas d'indexation des images
- `nocache` : Pas de mise en cache

**Vérification** :
```bash
curl -I https://VOTRE_DOMAINE.COM | grep -i "x-robots"
```

### Couche 4 : Header HTTP X-Robots-Tag (Nginx) ✅
**Fichier** : `deployment/nginx/linkedin-bot.conf`

**Fonction** : Header ajouté par Nginx (double sécurité)

**Efficacité** : ⭐⭐⭐⭐⭐ Excellente (même si Next.js échoue)

**Configuration** :
```nginx
add_header X-Robots-Tag "noindex, nofollow, noarchive, nosnippet, noimageindex, nocache" always;
```

**Vérification** :
```bash
curl -I https://VOTRE_DOMAINE.COM | grep -i "x-robots"
# Doit afficher : x-robots-tag: noindex, nofollow, ...
```

---

## 🧪 Tests de Vérification

### Test 1 : Vérifier robots.txt

```bash
# Doit retourner "Disallow: /"
curl https://VOTRE_DOMAINE.COM/robots.txt
```

**Résultat attendu** :
```
User-agent: *
Disallow: /
```

### Test 2 : Vérifier Meta Tags

```bash
# Doit contenir <meta name="robots" content="noindex...">
curl -s https://VOTRE_DOMAINE.COM | grep -o '<meta name="robots"[^>]*>'
```

**Résultat attendu** :
```html
<meta name="robots" content="noindex, nofollow, nocache">
```

### Test 3 : Vérifier Header HTTP

```bash
# Doit afficher "x-robots-tag: noindex..."
curl -I https://VOTRE_DOMAINE.COM | grep -i "x-robots"
```

**Résultat attendu** :
```
x-robots-tag: noindex, nofollow, noarchive, nosnippet, noimageindex, nocache
```

### Test 4 : Google Search Console

Attendez 1-2 semaines puis vérifiez que votre site n'apparaît pas dans Google :

```
site:VOTRE_DOMAINE.COM
```

**Résultat attendu** : Aucun résultat trouvé

---

## 🚨 Que faire si votre site est déjà indexé ?

### Étape 1 : Vérifier l'indexation actuelle

```bash
# Rechercher votre domaine dans Google
https://www.google.com/search?q=site:VOTRE_DOMAINE.COM
```

### Étape 2 : Demander la suppression immédiate

**Google Search Console** :
1. Allez sur https://search.google.com/search-console
2. Ajoutez votre propriété (domaine)
3. Allez dans **Suppressions** → **Nouvelle demande**
4. Entrez l'URL de votre dashboard
5. Sélectionnez "Supprimer temporairement l'URL"
6. Validez

**Délai** : 24-48 heures (temporaire)

### Étape 3 : Suppression définitive

Avec les protections en place (robots.txt + X-Robots-Tag), Google va :
1. Détecter le `noindex` lors du prochain crawl
2. Retirer votre site de l'index définitivement
3. **Délai** : 1-4 semaines

### Étape 4 : Bing / Autres moteurs

**Bing Webmaster Tools** :
1. https://www.bing.com/webmasters
2. Même processus que Google

**Autres moteurs** :
- Yandex : https://webmaster.yandex.com/
- DuckDuckGo : Respecte automatiquement robots.txt

---

## 📊 Monitoring Continu

### Alertes Google

Configurez une alerte Google pour être notifié si votre site apparaît :

1. Allez sur https://www.google.com/alerts
2. Créez une alerte avec : `site:VOTRE_DOMAINE.COM`
3. Fréquence : **Au fil de l'eau**
4. Email de notification : Votre email

### Script de Vérification Automatique

Ajoutez à votre cron quotidien :

```bash
#!/bin/bash
# /home/pi/check-indexation.sh

DOMAIN="VOTRE_DOMAINE.COM"
RESULTS=$(curl -s "https://www.google.com/search?q=site:${DOMAIN}" | grep -o "About [0-9,]* results")

if [ -n "$RESULTS" ]; then
  echo "⚠️ WARNING: Site appears to be indexed in Google!"
  echo "$RESULTS"
  # Envoyer email d'alerte
  echo "Site indexed: $RESULTS" | mail -s "ALERT: Dashboard Indexed" votre@email.com
else
  echo "✅ OK: Site not indexed"
fi
```

```bash
# Ajouter au cron
crontab -e
# Ajouter :
0 2 * * * /home/pi/check-indexation.sh
```

---

## 🔐 Protections Complémentaires

### 1. Authentification Obligatoire

Votre dashboard a déjà une authentification JWT, mais vous pouvez ajouter :

**Basic Auth Nginx** (double protection) :

```nginx
# Dans linkedin-bot.conf, section server
location / {
    auth_basic "Restricted Access";
    auth_basic_user_file /etc/nginx/.htpasswd;

    # ... reste de la config proxy ...
}
```

Créer le fichier `.htpasswd` :

```bash
sudo apt install apache2-utils
sudo htpasswd -c /etc/nginx/.htpasswd admin
# Entrer mot de passe
sudo systemctl reload nginx
```

### 2. IP Whitelisting

Limiter l'accès à votre IP uniquement :

```nginx
# Dans linkedin-bot.conf
location / {
    # Votre IP publique (à adapter)
    allow 1.2.3.4;
    deny all;

    # ... reste de la config ...
}
```

Trouver votre IP publique :

```bash
curl https://ifconfig.me
```

### 3. Blocage Géographique

Si vous êtes toujours en France, bloquer les autres pays :

```nginx
# Installer ngx_http_geoip_module
sudo apt install nginx-module-geoip

# Dans nginx.conf
http {
    geoip_country /usr/share/GeoIP/GeoIP.dat;

    map $geoip_country_code $allowed_country {
        default no;
        FR yes;  # France uniquement
    }
}

# Dans linkedin-bot.conf
if ($allowed_country = no) {
    return 403;
}
```

---

## 📝 Checklist Anti-Indexation

Avant de valider que tout est OK :

- [ ] `robots.txt` créé et accessible (`curl /robots.txt`)
- [ ] Meta tags noindex dans le code source (`curl -s / | grep robots`)
- [ ] Header X-Robots-Tag présent (`curl -I / | grep -i x-robots`)
- [ ] Nginx rechargé (`sudo systemctl reload nginx`)
- [ ] Dashboard redéployé (`docker compose restart dashboard`)
- [ ] Test Google Search (`site:VOTRE_DOMAINE.COM` = 0 résultats)
- [ ] Alerte Google configurée
- [ ] Script de monitoring en cron (optionnel)

---

## 🆘 Dépannage

### Problème : Header X-Robots-Tag absent

**Vérifier Next.js** :

```bash
# Redéployer dashboard
docker compose -f docker-compose.pi4-standalone.yml restart dashboard

# Vérifier logs
docker compose logs dashboard | grep -i "robots"
```

**Vérifier Nginx** :

```bash
# Tester config
sudo nginx -t

# Recharger
sudo systemctl reload nginx

# Vérifier logs
sudo tail -f /var/log/nginx/linkedin-bot-error.log
```

### Problème : Site toujours indexé après 2 semaines

1. Vérifier que les headers sont bien envoyés (`curl -I`)
2. Forcer recrawl Google Search Console → Inspection URL → Demander indexation
3. Google va détecter le `noindex` et supprimer
4. Patience : Peut prendre jusqu'à 1 mois

### Problème : Robots.txt non accessible

```bash
# Vérifier que le fichier existe
ls -la /home/pi/linkedin-birthday-auto/dashboard/public/robots.txt

# Next.js sert automatiquement /public/robots.txt sur /robots.txt
# Si pas accessible, vérifier build Next.js
docker compose logs dashboard
```

---

## 📚 Ressources

- [Google : Gérer l'indexation](https://developers.google.com/search/docs/crawling-indexing/block-indexing)
- [Robots.txt Specification](https://www.robotstxt.org/)
- [X-Robots-Tag Documentation](https://developers.google.com/search/docs/crawling-indexing/robots-meta-tag)

---

**Auteur** : Audit Sécurité 2025
**Version** : 1.0
**Date** : 10 Décembre 2025
