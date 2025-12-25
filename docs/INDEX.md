# 📚 Documentation Index

**LinkedIn Birthday Auto Bot** - Navigation complète de la documentation du projet.

---

## 🚀 Démarrage Rapide (Version V1 Stable)

**👉 Commencez ici si vous êtes nouveau :**

- **[QUICK_START_2025.md](QUICK_START_2025.md)** - Installation et configuration en 10 minutes
  - Prérequis, étapes d'installation, accès au dashboard
  - Pour démarrer rapidement sur Raspberry Pi 4

---

## 🏗️ Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Spécifications techniques complètes V1
  - Architecture micro-services, bots détaillés, API routes, schéma base de données

- **[SCHEDULER_API.md](SCHEDULER_API.md)** - Documentation API Scheduler V1
  - Endpoints REST complets pour gérer les jobs
  - Exemples requête/réponse JSON

- **[../app_v2/README.md](../app_v2/README.md)** - **Nouveau :** Architecture V2 (Expérimentale)
  - Détails sur la refonte Async-First (FastAPI + SQLAlchemy)

---

## 🔐 Sécurité & Configuration

- **[SECURITY.md](SECURITY.md)** - Guides sécurité et hardening
  - Sécurité du système, protection des données, bonnes pratiques

- **[HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md)** - Configuration SSL/TLS
  - 4 options : LAN, Let's Encrypt, certificats existants, manuel
  - Setup et troubleshooting HTTPS

- **[PASSWORD_MANAGEMENT_GUIDE.md](PASSWORD_MANAGEMENT_GUIDE.md)** - Gestion des mots de passe
  - Hachage bcrypt robuste
  - Change, reset, récupération mot de passe

- **[SETUP_BACKUP_GUIDE.md](SETUP_BACKUP_GUIDE.md)** - Sauvegardes Google Drive
  - Configuration automatisée rclone
  - Backup quotidien avec encryption

---

## 🛠️ Dépannage & Support

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Guide complet de dépannage
  - Setup, Docker, HTTPS, backups, dashboard, API

---

## 📖 Rapports & Analyses (Archive)

Documentation historique et audits :

- **[audit/AUDIT_REPORT_COMPLETE.md](audit/AUDIT_REPORT_COMPLETE.md)** - **Audit V2 :** Analyse complète de la version expérimentale
- **[audit/AUDIT_V1.md](audit/AUDIT_V1.md)** - Audit de la version stable V1
- **[archive/AUDIT_REPORT_2025-01.md](archive/AUDIT_REPORT_2025-01.md)** - Audit historique Janvier 2025
- **[archive/IMPLEMENTATION_SUMMARY_2025.md](archive/IMPLEMENTATION_SUMMARY_2025.md)** - Résumé historique des implémentations
- **[archive/HISTORY_ANALYSIS_2025.md](archive/HISTORY_ANALYSIS_2025.md)** - Contexte historique et leçons apprises

---

## 🎯 Guides Rapides par Scénario

### Je viens de cloner le repo
1. Lire [QUICK_START_2025.md](QUICK_START_2025.md)
2. Lancer `./setup.sh` (Déploie la V1 Stable)
3. Accéder au dashboard à `https://<IP_RPI>`

### Je suis développeur et je veux voir la V2
1. Lire [../app_v2/README.md](../app_v2/README.md)
2. Consulter [audit/AUDIT_REPORT_COMPLETE.md](audit/AUDIT_REPORT_COMPLETE.md)
3. Configurer l'environnement local Python pour `app_v2/`

### J'ai une erreur ou problème (V1)
1. Consulter [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

---

## 📊 Fichiers de Configuration

- **README.md** - Vue d'ensemble projet (V1 vs V2)
- **CHANGELOG.md** - Historique versions
- **docker-compose.yml** - Orchestration services V1
- **config/config.yaml** - Configuration bots V1

---

**Version Documentation** : Décembre 2025
**État** : Consolidation V1 (Production) et V2 (Beta)
