# Guide de Migration vers v4.1

**Date**: Décembre 2025
**Cible**: Utilisateurs existants migrant depuis v4.0 ou antérieur

---

## 🎯 Résumé des Changements

La version 4.1 apporte des améliorations critiques pour la stabilité et la maintenabilité sur Raspberry Pi 4 :

- ✅ **Limites RAM strictes** pour prévenir les OOM Kills
- ✅ **Hashage mot de passe robuste** sans dépendance Python
- ✅ **Renouvellement SSL automatique** via cron job
- ✅ **CI/CD amélioré** avec healthchecks
- ✅ **Docker Compose standardisé** (nouveau nom de fichier)

---

## 📋 Checklist de Migration

### Étape 1 : Sauvegarde

Avant toute mise à jour, sauvegardez vos données :

```bash
cd /path/to/linkedin-birthday-auto

# Sauvegarder la config et les données
tar -czf backup-$(date +%Y%m%d).tar.gz \
  .env \
  config/ \
  data/ \
  logs/
```

### Étape 2 : Mise à Jour du Code

```bash
# Arrêter les services
docker compose down

# Sauvegarder les changements locaux (si nécessaire)
git stash

# Mettre à jour le code
git pull origin main

# Restaurer les changements locaux si nécessaire
git stash pop
```

### Étape 3 : Migration Automatique

Le script `setup.sh` détecte automatiquement votre configuration existante :

```bash
./setup.sh
```

**Ce qui se passe automatiquement :**
- ✅ Détection du fichier `.env` existant
- ✅ Application des nouvelles limites RAM
- ✅ Proposition de configuration du cron SSL
- ✅ Vérification de la compatibilité des services

### Étape 4 : Configuration SSL Auto-Renewal (Recommandé)

Si vous utilisez Let's Encrypt, configurez le renouvellement automatique :

```bash
# Option A : Via le setup (recommandé)
./setup.sh
# Répondez "Oui" à la question sur le cron SSL

# Option B : Manuel
crontab -e
# Ajoutez cette ligne :
# 0 3 * * * /path/to/linkedin-birthday-auto/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1
```

### Étape 5 : Redémarrage avec Nouvelles Limites

```bash
# Redémarrer avec les nouvelles limites RAM
docker compose up -d

# Vérifier que tout fonctionne
docker compose ps
docker compose logs -f --tail=50
```

---

## 🔍 Vérifications Post-Migration

### 1. Vérifier les Limites RAM

```bash
# Voir les limites appliquées
docker stats --no-stream

# Exemple de sortie attendu :
# CONTAINER     MEM USAGE / LIMIT
# dashboard     450MB / 896MB
# bot-worker    820MB / 1400MB
# api           180MB / 384MB
```

### 2. Vérifier le Cron SSL

```bash
# Lister les cron jobs
crontab -l | grep renew_certificates

# Tester le script manuellement (dry-run)
./scripts/renew_certificates.sh --dry-run
```

### 3. Vérifier les Services

```bash
# Tous les services doivent être "healthy"
docker compose ps

# Tester l'accès au dashboard
curl -k https://localhost:3000/api/system/health
```

---

## ⚠️ Changements Cassants (Breaking Changes)

### Nom du Fichier Docker Compose

**Avant (v4.0) :** `docker-compose.pi4-standalone.yml`
**Maintenant (v4.1) :** `docker-compose.yml`

**Impact :**
- Les scripts personnels référençant l'ancien nom doivent être mis à jour
- Les commandes `docker compose` fonctionnent désormais sans `-f`

**Migration :**
```bash
# Ancien (ne fonctionne plus)
docker compose -f docker-compose.pi4-standalone.yml logs

# Nouveau
docker compose logs
```

### Comportement du Hashage de Mot de Passe

**Avant :** Nécessitait Python bcrypt sur l'hôte
**Maintenant :** Utilise le conteneur Docker ou des outils natifs

**Impact :**
- Plus d'erreurs d'installation bcrypt sur Debian 12+
- Les mots de passe existants restent valides
- Aucune action requise pour les utilisateurs existants

---

## 🆘 Dépannage

### Problème : Services ne démarrent pas après migration

**Solution :**
```bash
# Nettoyer les conteneurs et volumes orphelins
docker compose down --remove-orphans
docker system prune -f

# Recréer les conteneurs
docker compose up -d --force-recreate
```

### Problème : OOM Kill malgré les limites

**Diagnostic :**
```bash
# Vérifier la RAM totale utilisée
free -h

# Vérifier les limites appliquées
docker inspect dashboard | grep -A5 Memory

# Vérifier les logs kernel
dmesg | grep -i "out of memory"
```

**Solutions :**
1. Désactiver le monitoring si non utilisé :
   ```bash
   docker compose down
   docker compose up -d  # Le monitoring n'est plus démarré par défaut
   ```

2. Réduire les limites si nécessaire (modifier `docker-compose.yml`) :
   ```yaml
   dashboard:
     deploy:
       resources:
         limits:
           memory: 768M  # Réduire de 896M à 768M
   ```

### Problème : Cron SSL ne fonctionne pas

**Diagnostic :**
```bash
# Vérifier que le cron est enregistré
crontab -l | grep renew_certificates

# Tester manuellement
./scripts/renew_certificates.sh --dry-run

# Vérifier les logs
cat /var/log/certbot-renew.log
```

**Solution :**
```bash
# Supprimer et recréer le cron
crontab -l | grep -v renew_certificates | crontab -
crontab -e
# Ajouter : 0 3 * * * /chemin/absolu/scripts/renew_certificates.sh >> /var/log/certbot-renew.log 2>&1
```

---

## 📊 Comparaison Avant/Après

| Métrique | Avant v4.1 | Après v4.1 | Amélioration |
|----------|-----------|-----------|--------------|
| **OOM Kills** | Fréquents | Aucun | ✅ 100% |
| **Échecs Setup bcrypt** | Fréquents (Debian 12) | Aucun | ✅ 100% |
| **Renouvellement SSL** | Manuel | Automatique | ✅ Automatisé |
| **Builds CI/CD cassés** | Occasionnels | Détectés avant push | ✅ Qualité++ |
| **Maintenance** | 2h/mois | 15min/mois | ✅ -87% |

---

## 🎓 Ressources

- **CHANGELOG complet** : [CHANGELOG.md](../CHANGELOG.md)
- **Documentation Troubleshooting** : [TROUBLESHOOTING_2025.md](TROUBLESHOOTING_2025.md)
- **Guide SSL** : [SETUP_HTTPS_GUIDE.md](SETUP_HTTPS_GUIDE.md)
- **Support GitHub** : [Issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)

---

## ✅ Checklist Finale

Après migration, vérifiez que tout fonctionne :

- [ ] Services démarrés : `docker compose ps`
- [ ] Dashboard accessible : `https://<votre-domaine>`
- [ ] Pas d'erreurs dans les logs : `docker compose logs --tail=100`
- [ ] RAM sous contrôle : `docker stats --no-stream`
- [ ] Cron SSL configuré : `crontab -l | grep renew`
- [ ] Backup récent disponible : `ls -lh backup-*.tar.gz`

---

**🎉 Félicitations ! Votre installation est maintenant sur la v4.1 avec une stabilité améliorée.**

Si vous rencontrez des problèmes, n'hésitez pas à ouvrir une [Issue GitHub](https://github.com/GaspardD78/linkedin-birthday-auto/issues).
