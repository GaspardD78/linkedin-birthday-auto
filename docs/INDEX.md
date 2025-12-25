# 📚 Documentation Index

**LinkedIn Birthday Auto Bot** - Navigation complète de la documentation du projet.

**Décembre 2025** - Mise à jour complète : V1 en production, V2 en développement.

---

## ⚠️ État du Projet

- **V1 (Production)** ✅ : Version 4.1 stable, déployée sur Raspberry Pi 4. **À utiliser pour la production.**
- **V2 (Alternative)** 🔄 : Refonte async-first en `./app_v2/`, en développement. Voir `APP_V2_ANALYSIS_REPORT.md` pour les détails.

---

## 🚀 Démarrage Rapide (V1 - Production)

**👉 Commencez ici si vous êtes nouveau :**

- **[QUICK_START_2025.md](QUICK_START_2025.md)** - Installation et configuration en 10 minutes
  - Prérequis, étapes d'installation, accès au dashboard
  - Pour démarrer rapidement sur Raspberry Pi 4

---

## 🏗️ Architecture & Design

- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Spécifications techniques complètes
  - Architecture micro-services, bots détaillés, API routes, schéma base de données

- **[SCHEDULER_API.md](SCHEDULER_API.md)** - Documentation API Scheduler (Jan 2025)
  - Endpoints REST complets pour gérer les jobs
  - Exemples requête/réponse JSON
  - Authentification et rate limiting
  - Voir aussi: [src/scheduler/README.md](../src/scheduler/README.md) pour l'architecture interne

---

## 🔐 Sécurité & Configuration

- **[SECURITY.md](SECURITY.md)** - Guides sécurité et hardening
  - Sécurité du système, protection des données, bonnes pratiques
  - Essentiels pour production

- **[HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md)** - Configuration SSL/TLS
  - 4 options : LAN, Let's Encrypt, certificats existants, manuel
  - Setup et troubleshooting HTTPS
  - Auto-renouvellement certificats Let's Encrypt

- **[PASSWORD_MANAGEMENT_GUIDE.md](PASSWORD_MANAGEMENT_GUIDE.md)** - Gestion des mots de passe
  - Hachage bcrypt robuste
  - Change, reset, récupération mot de passe
  - Scripts de gestion post-setup

- **[SETUP_BACKUP_GUIDE.md](SETUP_BACKUP_GUIDE.md)** - Sauvegardes Google Drive
  - Configuration automatisée rclone
  - Backup quotidien avec encryption
  - Test restore mensuel et notifications Slack

---

## 🛠️ Dépannage & Support

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Guide complet de dépannage
  - Problèmes courants et solutions par catégorie
  - Setup, Docker, HTTPS, backups, dashboard, API
  - Progressif (solutions simples → avancées)

---

## 🔬 Analyses & Rapports

### V2 (Alternative)

- **[../APP_V2_ANALYSIS_REPORT.md](../APP_V2_ANALYSIS_REPORT.md)** ⚠️ **Lecture essentielle pour V2**
  - Analyse complète de l'architecture V2 en `./app_v2/`
  - Points forts et problèmes critiques identifiés
  - Recommandations pour la production
  - **Verdict :** Architecture excellente mais sécurité problématique, pas de tests

### V1 (Production)

- **[archive/AUDIT_REPORT_2025-01.md](archive/AUDIT_REPORT_2025-01.md)** - Audit complet du code V1
- **[archive/IMPLEMENTATION_SUMMARY_2025.md](archive/IMPLEMENTATION_SUMMARY_2025.md)** - Résumé des implémentations (Jan 2025)
- **[archive/DESIGN_HTTPS_GDRIVE_SECURITY_2025.md](archive/DESIGN_HTTPS_GDRIVE_SECURITY_2025.md)** - Architecture HTTPS & Google Drive
- **[archive/SECURITY_ENHANCEMENTS_2025.md](archive/SECURITY_ENHANCEMENTS_2025.md)** - Améliorations sécurité (Grafana, Docker, Rate Limiting)
- **[archive/HISTORY_ANALYSIS_2025.md](archive/HISTORY_ANALYSIS_2025.md)** - Contexte historique et leçons apprises
- **[archive/MIGRATION_V4.1.md](archive/MIGRATION_V4.1.md)** - Guide migration version 4.1
- **[archive/PHASE5_DOCKER_PULL_FIX.md](archive/PHASE5_DOCKER_PULL_FIX.md)** - Fix Docker pull issues
- **[archive/SETUP_IMPROVEMENTS.md](archive/SETUP_IMPROVEMENTS.md)** - Améliorations du script setup.sh

---

## 🎯 Guides Rapides par Scénario

### Je suis nouveau, je veux démarrer (V1)
1. Lire [QUICK_START_2025.md](QUICK_START_2025.md) (recommandé)
2. Lancer `./setup.sh`
3. Accéder au dashboard à `https://<IP_RPI>`
4. (Optionnel) Lire [ARCHITECTURE.md](ARCHITECTURE.md) pour comprendre les détails techniques

### Je veux explorer l'architecture V2 alternative
1. Consulter [../APP_V2_ANALYSIS_REPORT.md](../APP_V2_ANALYSIS_REPORT.md) - **C'est important!**
2. Explorer le code dans `./app_v2/`
3. Note : Non recommandée pour production sans correction des problèmes sécurité

### J'ai une erreur ou problème
1. Consulter [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
2. Rechercher symptôme et suivre solutions progressives

### Je dois configurer HTTPS
1. Lire [HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md)
2. Choisir option (LAN / Let's Encrypt / Custom / Manuel)
3. Suivre les étapes de configuration correspondantes

### Je dois changer mon mot de passe
1. Consulter [PASSWORD_MANAGEMENT_GUIDE.md](PASSWORD_MANAGEMENT_GUIDE.md)
2. Lancer `./scripts/manage_dashboard_password.sh`
3. Suivre les prompts interactifs

### Je veux activer les sauvegardes Google Drive
1. Lire [SETUP_BACKUP_GUIDE.md](SETUP_BACKUP_GUIDE.md)
2. Lancer `./scripts/setup_gdrive_backup.sh` (si non fait en setup)
3. Configurer rclone et test restore

### Je dois comprendre l'architecture
1. Consulter [ARCHITECTURE.md](ARCHITECTURE.md)
2. Lire schémas data flow et spécifications
3. Consulter rapports [archive/](archive/) pour détails techniques

### Je dois vérifier/durcir la sécurité
1. Lire [SECURITY.md](SECURITY.md)
2. Consulter rapport [AUDIT_REPORT_2025-01.md](archive/AUDIT_REPORT_2025-01.md)
3. Mettre en place recommandations

---

## 📊 Fichiers de Configuration

Fichiers de configuration importants (hors docs/) :

- **README.md** - Vue d'ensemble projet et features
- **CHANGELOG.md** - Historique versions et changements
- **docker-compose.yml** - Orchestration services
- **config/config.yaml** - Configuration bots et fonctionnalités
- **.env.pi4.example** - Variables d'environnement exemple

---

## 🔗 Liens Utiles

- **GitHub Repo** - https://github.com/GaspardD78/linkedin-birthday-auto
- **Issues & Discussions** - Ouvrir issue sur GitHub
- **Let's Encrypt** - https://letsencrypt.org/
- **Raspberry Pi Docs** - https://www.raspberrypi.com/documentation/

---

## 💡 Notes

- 📌 **Checklist production** : Lire [SECURITY.md](SECURITY.md) + [HTTPS_CONFIGURATION.md](HTTPS_CONFIGURATION.md)
- 📌 **RPi4 optimisation** : Limites RAM strictes, ZRAM/Swap automatique
- 📌 **Certificats** : Auto-renouvelés automatiquement (Let's Encrypt ou script cron)
- 📌 **Backups** : Recommandé Google Drive avec encryption (quotidien)

---

**Version Documentation** : 3.0 (2025-12)
**Mise à jour** : Consolidation complète - Suppression fichiers obsolètes, clarification V1/V2, organisation par thème
**Fichiers supprimés** : AUDIT_REPORT_COMPLETE.md, SETUP_ANALYSIS_REPORT.md, RAPPORT_ANALYSE_SETUP.md, TEST_RESULTS.md, SETUP_CORRECTIONS_APPLIED.md, SETUP_GUIDE.md, BCRYPT_ARM64_FIX.md, DNS_FIX_SUMMARY.md, DOCKER_DNS_ANALYSIS.md, CORRECTIONS_AUDIT_PHASE1.md, PROJECT_MASTER_DOC.md (archivé)
