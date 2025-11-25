# 🔄 Guide de Mise à Jour - Déploiement Pi4

Ce guide explique comment appliquer les optimisations de l'audit **sans tout reconstruire**.

---

## 🎯 Stratégies de mise à jour

### Option 1️⃣ : Mise à jour automatique (RECOMMANDÉE)

**✅ Avantages** : Simple, rapide, préserve les données
**⏱️ Durée** : ~2 minutes
**📉 Downtime** : ~30 secondes

```bash
# 1. Récupérer les dernières modifications
git pull origin claude/audit-phase2-raspberry-pi-01BCXqhDv2FvawTpHFXxJHPi

# 2. Exécuter le script de mise à jour
./scripts/update_deployment_pi4.sh
```

**Ce que fait le script** :
- ✅ Sauvegarde automatique de la base de données
- ✅ Recrée les conteneurs avec nouvelles limites RAM/CPU
- ✅ Préserve les volumes (données, logs)
- ✅ Vérifie la santé des services
- ✅ Nettoie les images inutiles

---

### Option 2️⃣ : Mise à jour manuelle service par service

**✅ Avantages** : Contrôle total, downtime minimal
**⏱️ Durée** : ~5 minutes
**📉 Downtime** : ~10 secondes par service

```bash
# 1. Mettre à jour un service à la fois
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate --no-build bot-worker

# 2. Vérifier que le service redémarre correctement
docker compose -f docker-compose.pi4-standalone.yml logs -f bot-worker

# 3. Répéter pour les autres services
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate --no-build dashboard
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate --no-build redis-bot
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate --no-build redis-dashboard
```

---

### Option 3️⃣ : Mise à jour avec reconstruction d'images

**⚠️ À utiliser si** : Modifications du code source Python/TypeScript
**⏱️ Durée** : ~15-20 minutes
**📉 Downtime** : ~5 minutes

```bash
# 1. Arrêter les services
docker compose -f docker-compose.pi4-standalone.yml down

# 2. Rebuild les images
docker compose -f docker-compose.pi4-standalone.yml build

# 3. Redémarrer
docker compose -f docker-compose.pi4-standalone.yml up -d
```

---

## 📋 Checklist pré-mise à jour

Avant de lancer la mise à jour, vérifiez :

```bash
# 1. Espace disque disponible (min 5GB recommandé)
df -h /

# 2. Température CPU acceptable (<70°C)
vcgencmd measure_temp

# 3. Pas de processus bloquant
docker compose -f docker-compose.pi4-standalone.yml ps

# 4. Sauvegarde manuelle (optionnel mais recommandé)
cp data/linkedin_automation.db data/linkedin_automation.db.backup
```

---

## 🔍 Vérification post-mise à jour

### 1. Vérifier que tous les services tournent

```bash
docker compose -f docker-compose.pi4-standalone.yml ps
```

Résultat attendu : Tous les services en **UP**

### 2. Vérifier les nouvelles limites RAM

```bash
docker stats --no-stream
```

Résultat attendu :
```
NAME                      MEM USAGE / LIMIT
linkedin-bot-worker       ~600M / 900M     ✅
linkedin-dashboard        ~450M / 700M     ✅
linkedin-bot-redis        ~30M / 300M      ✅
linkedin-dashboard-redis  ~20M / 150M      ✅
```

### 3. Vérifier les logs

```bash
# Logs du bot
docker compose -f docker-compose.pi4-standalone.yml logs --tail=50 bot-worker

# Logs du dashboard
docker compose -f docker-compose.pi4-standalone.yml logs --tail=50 dashboard
```

Pas d'erreurs de type `Out of Memory` ou `Cannot allocate memory`

### 4. Tester le dashboard

```bash
# Obtenir l'IP du Pi4
hostname -I | awk '{print $1}'

# Accéder au dashboard
# http://<IP_PI4>:3000
```

### 5. Vérifier la rotation des logs Docker

```bash
# Vérifier la config de rotation
docker inspect linkedin-bot-worker | grep -A5 "LogConfig"
```

Résultat attendu :
```json
"LogConfig": {
    "Type": "json-file",
    "Config": {
        "max-size": "5m",
        "max-file": "2",
        "compress": "true"
    }
}
```

---

## 🚨 Résolution de problèmes

### Problème 1 : Service ne démarre pas après mise à jour

**Symptômes** : Container en état `Restarting` ou `Exited`

**Solution** :
```bash
# Voir les logs d'erreur
docker compose -f docker-compose.pi4-standalone.yml logs --tail=100 <service_name>

# Redémarrer en mode verbose
docker compose -f docker-compose.pi4-standalone.yml up <service_name>
```

**Causes courantes** :
- Limite RAM trop basse → Augmenter temporairement dans docker-compose
- Port déjà utilisé → Vérifier avec `netstat -tulpn`
- Volume manquant → Vérifier `docker volume ls`

---

### Problème 2 : Base de données non trouvée

**Symptômes** : `sqlite3.OperationalError: unable to open database file`

**Solution** :
```bash
# Vérifier l'emplacement de la DB
ls -lh data/linkedin_automation.db

# Si DB à la racine, migrer
mkdir -p data
mv linkedin_automation.db data/

# Corriger permissions
chmod 666 data/linkedin_automation.db
chmod 777 data
```

---

### Problème 3 : Out of Memory (OOM)

**Symptômes** : Container tué brutalement, logs `Killed`

**Solution immédiate** :
```bash
# Augmenter temporairement la limite RAM
# Éditer docker-compose.pi4-standalone.yml
memory: 900M → memory: 1.0G  # Bot Worker
memory: 700M → memory: 800M  # Dashboard

# Redémarrer
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate
```

**Solution long terme** : Activer ZRAM (voir ci-dessous)

---

### Problème 4 : Dashboard très lent après mise à jour

**Symptômes** : Next.js prend >2 minutes à répondre

**Causes** :
- Limite RAM trop basse (700M peut être juste au 1er démarrage)
- Swap utilisé massivement

**Solution** :
```bash
# Vérifier utilisation SWAP
free -h

# Si SWAP > 1GB, c'est le problème
# Augmenter temporairement limite dashboard
memory: 700M → memory: 900M

# Puis activer ZRAM (voir section suivante)
```

---

## 🗜️ Activer ZRAM (Recommandé)

ZRAM compresse la RAM (ratio 3:1) pour éviter le swap sur SD card.

### Installation

```bash
# 1. Installer zram-tools
sudo apt-get update
sudo apt-get install -y zram-tools

# 2. Configurer (2GB compressé = ~6GB utilisable)
sudo tee /etc/default/zramswap << EOF
# Compression ratio: 3:1 typical
ALGO=lz4
PERCENT=50
EOF

# 3. Activer
sudo systemctl enable zramswap
sudo systemctl start zramswap

# 4. Vérifier
zramctl
```

### Résultat attendu

```
NAME       ALGORITHM DISKSIZE DATA COMPR TOTAL STREAMS MOUNTPOINT
/dev/zram0 lz4            2G  12M   3M   12K       4 [SWAP]
```

**Impact** :
- ✅ -50% utilisation SWAP (SD card)
- ✅ +2GB mémoire disponible (compressée)
- ✅ Meilleures performances globales

---

## 📊 Monitoring continu

### Script de monitoring automatique

```bash
# Lancer monitoring en arrière-plan
nohup ./scripts/monitor_pi4_resources.sh 300 > logs/monitoring.log 2>&1 &

# Voir le monitoring
tail -f logs/monitoring.log
```

### Alertes température

```bash
# Créer un script d'alerte
cat > /usr/local/bin/check_pi_temp.sh << 'EOF'
#!/bin/bash
TEMP=$(vcgencmd measure_temp | grep -oP '\d+\.\d+')
if (( $(echo "$TEMP > 75" | bc -l) )); then
    echo "ALERTE: Température CPU élevée: ${TEMP}°C" | logger -t pi4-temp
    # Envoyer notification (optionnel)
fi
EOF

chmod +x /usr/local/bin/check_pi_temp.sh

# Ajouter à cron (toutes les 5 minutes)
(crontab -l 2>/dev/null; echo "*/5 * * * * /usr/local/bin/check_pi_temp.sh") | crontab -
```

---

## 🔄 Rollback (retour en arrière)

Si la mise à jour pose problème :

### Rollback rapide (conteneurs uniquement)

```bash
# 1. Restaurer l'ancienne version du docker-compose
git checkout HEAD~1 docker-compose.pi4-standalone.yml

# 2. Recréer les conteneurs
docker compose -f docker-compose.pi4-standalone.yml up -d --force-recreate

# 3. Vérifier
docker compose -f docker-compose.pi4-standalone.yml ps
```

### Rollback complet (avec données)

```bash
# 1. Identifier la sauvegarde
ls -lht backups/

# 2. Restaurer la base de données
cp backups/YYYYMMDD_HHMMSS/linkedin_automation.db data/

# 3. Restaurer la config
cp backups/YYYYMMDD_HHMMSS/config.yaml config/

# 4. Redémarrer
docker compose -f docker-compose.pi4-standalone.yml restart
```

---

## ✅ Résumé des commandes rapides

```bash
# Mise à jour automatique (RECOMMANDÉ)
./scripts/update_deployment_pi4.sh

# Vérifier statut
docker compose -f docker-compose.pi4-standalone.yml ps

# Voir les logs
docker compose -f docker-compose.pi4-standalone.yml logs -f

# Voir les stats RAM/CPU
docker stats

# Redémarrer un service
docker compose -f docker-compose.pi4-standalone.yml restart bot-worker

# Monitoring continu
./scripts/monitor_pi4_resources.sh 300

# Nettoyage
./scripts/cleanup_pi4.sh
```

---

## 📞 Support

En cas de problème :

1. **Vérifier les logs** : `docker compose logs -f <service>`
2. **Vérifier les ressources** : `./scripts/monitor_pi4_resources.sh`
3. **Consulter** : `AUDIT_PHASE2_RASPBERRY_PI4.md`
4. **Rollback** si nécessaire (voir section ci-dessus)

---

**Mise à jour réussie ? 🎉**

N'oubliez pas :
- ✅ Activer ZRAM pour meilleures performances
- ✅ Planifier le nettoyage hebdomadaire (cron)
- ✅ Surveiller la température (dissipateur recommandé)
