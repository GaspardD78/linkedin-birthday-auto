# 📋 PLAN DE BATAILLE - LinkedIn Auto RPi4

> **Date de l'audit**: 2025-01-18
> **Cible**: Raspberry Pi 4 (4GB RAM, SD 32GB, ARM64)

---

## 🎯 OBJECTIFS

1. **Zéro crash OOM** (Out Of Memory)
2. **Sécurité maximale** (HTTPS, UFW, bcrypt)
3. **Longévité SD Card** (minimiser les écritures)

---

## ✅ DÉJÀ EN PLACE (Confirmé par l'audit)

| Élément | Fichier | Status |
|---------|---------|--------|
| BaseBot Pattern | `src/core/base_bot.py` | ✅ OK |
| Browser cleanup | `src/core/browser_manager.py:233-247` | ✅ OK |
| SQLite WAL | `src/core/database.py:106-123` | ✅ OK |
| Log rotation | `src/utils/logging.py:39-46` | ✅ OK |
| Docker GHCR images | `docker-compose.pi4-standalone.yml` | ✅ OK |
| DNS fiables | `docker-compose.pi4-standalone.yml` | ✅ OK |
| Swap auto | `setup.sh:287-319` | ✅ OK |

---

## 🔧 PLAN DE CORRECTION ORDONNÉ

### Phase 1 : Scripts de Maintenance (FAIT)

| # | Action | Fichier | Priorité |
|---|--------|---------|----------|
| 1 | ✅ Créer `setup_security_modern.sh` | `scripts/setup_security_modern.sh` | HAUTE |
| 2 | ✅ Restaurer `monitor_pi4_health.sh` | `scripts/monitor_pi4_health.sh` | HAUTE |
| 3 | ✅ Restaurer `verify_security.sh` | `scripts/verify_security.sh` | MOYENNE |

### Phase 2 : Intégration Setup Principal

| # | Action | Fichier | Description |
|---|--------|---------|-------------|
| 4 | Intégrer ZRAM dans `setup.sh` | `setup.sh` | Ajouter option ZRAM en plus du swap fichier |
| 5 | Ajouter appel au cron maintenance | `setup.sh` | Installer automatiquement le cron |
| 6 | Appeler `setup_security_modern.sh` | `setup.sh` | Option `--secure` pour setup complet |

### Phase 3 : Amélioration Docker Compose

| # | Action | Fichier | Description |
|---|--------|---------|-------------|
| 7 | Ajouter healthcheck Nginx amélioré | `docker-compose.pi4-standalone.yml` | Test HTTP en plus de `nginx -t` |
| 8 | Réduire mémoire Prometheus | `docker-compose.pi4-standalone.yml` | Limiter à 256MB |
| 9 | Ajouter politique restart | `docker-compose.pi4-standalone.yml` | `restart_policy: max_restarts: 3` |

### Phase 4 : Documentation

| # | Action | Fichier | Description |
|---|--------|---------|-------------|
| 10 | Documenter USB storage | `docs/USB_STORAGE_SETUP.md` | Pour déport DB/logs hors SD |
| 11 | Guide maintenance | `docs/MAINTENANCE_RPI4.md` | Procédures de maintenance |
| 12 | Checklist sécurité | `docs/SECURITY_CHECKLIST.md` | Liste avant mise en production |

---

## 📊 MATRICE DES RISQUES

| Risque | Impact | Probabilité | Mitigation |
|--------|--------|-------------|------------|
| OOM Crash | 🔴 Critique | 🟡 Moyen | ZRAM + Swap + Limites Docker |
| SD Card Usure | 🟠 Élevé | 🟠 Élevé | Log rotation + USB storage |
| Session LinkedIn | 🔴 Critique | 🟡 Moyen | Notifications + Auth check |
| Fuite mémoire Browser | 🔴 Critique | 🟢 Faible | Context/Browser close dans teardown |
| Contention SQLite | 🟠 Élevé | 🟢 Faible | WAL + busy_timeout + retry |

---

## 🚀 COMMANDES DE DÉPLOIEMENT

```bash
# 1. Sécurisation complète (root requis)
sudo ./scripts/setup_security_modern.sh --auto --domain votre-domaine.com

# 2. Déploiement standard
./setup.sh

# 3. Vérification sécurité
./scripts/verify_security.sh

# 4. Monitoring santé
./scripts/monitor_pi4_health.sh
```

---

## 📁 FICHIERS MODIFIÉS/CRÉÉS

```
scripts/
├── setup_security_modern.sh  [NOUVEAU] - Setup sécurité automatisé
├── monitor_pi4_health.sh     [RESTAURÉ] - Monitoring CPU/RAM/Disk
├── verify_security.sh        [RESTAURÉ] - Audit sécurité
└── cleanup_pi4.sh            [EXISTANT] - Nettoyage complet

docs/
└── PLAN_CORRECTION_RPI4.md   [NOUVEAU] - Ce document
```

---

## ✨ AMÉLIORATIONS FUTURES (Non Critiques)

1. **Prometheus remote_write** vers Grafana Cloud (monitoring externe)
2. **Alertmanager** pour notifications Telegram/Slack
3. **Backup incrémental** via restic vers S3/B2
4. **Watchtower** pour mise à jour auto des images Docker
5. **Fail2ban** pour protection SSH avancée

---

*Document généré automatiquement par l'audit de sécurité*
