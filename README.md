# 🤖 LinkedIn Birthday Auto Bot (RPi4 Optimized)

[![Build Status](https://img.shields.io/github/actions/workflow/status/GaspardD78/linkedin-birthday-auto/build-images.yml?branch=main)](https://github.com/GaspardD78/linkedin-birthday-auto/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/release/python-3110/)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

**Système autonome d'automatisation LinkedIn conçu pour Raspberry Pi 4.**
Gère vos vœux d'anniversaire et vos visites de profils de manière intelligente, discrète et résiliente.

---

## ✨ Fonctionnalités Clés

*   **⚡ Optimisé RPi4** : Consommation RAM minimale (~600MB), gestion ZRAM/Swap automatique, Docker multi-arch (ARM64).
*   **🎂 Birthday Bot** : Envoi de messages personnalisés (Jour J ou rattrapage).
*   **🔍 Visitor Bot** : Visite automatique de profils ciblés (Mode Recruteur, Filtres Booléens).
*   **🛡️ Sécurité Renforcée (V3.3+)** :
    *   **Conteneurs non-privilégiés** : L'API n'a plus d'accès root à l'hôte.
    *   **Docker Socket Proxy** : Gestion sécurisée des services via l'API Docker.
    *   **Isolation Réseau** : DNS fiables (Cloudflare/Google) forcés et hardening Nginx.
    *   **Rapport Sécurité Automatisé** : Vérification 4-points avec score (0-4) à chaque setup.
*   **🔐 Gestion HTTPS Intelligente (Jan 2025)** :
    *   **Menu Configuration HTTPS** : 4 options (LAN / Let's Encrypt / Certificats existants / Manuel).
    *   **Setup Let's Encrypt Automatisé** : Certificats générés et gérés automatiquement.
    *   **Import Certificats Existants** : Support certificats custom ou d'autorités tierces.
*   **💾 Sauvegardes Google Drive Intégrées (Jan 2025)** :
    *   **Configuration Automatisée** : Wizard interactif pour setup Google Drive + rclone.
    *   **Backup Quotidien** : Cron ajouté automatiquement (02:00 chaque jour).
    *   **Test Restore Mensuel** : Validation automatique de l'intégrité des backups.
    *   **Notifications Slack (Optionnel)** : Alertes backup success/failure via Slack.
*   **🔑 Gestion Mot de Passe Sécurisée (Jan 2025)** :
    *   **Hachage Bcrypt Robuste** : Mots de passe jamais stockés en clair.
    *   **Script de Modification** : Change/reset/status facilement post-setup.
    *   **Récupération en cas d'Oubli** : Réinitialisation avec mot de passe temporaire sécurisé.
*   **📊 Dashboard** : Interface Web Next.js pour le pilotage, les logs et les statistiques.
*   **🔄 Résilient** : Retry automatique, gestion des timeouts réseaux, base de données SQLite WAL robuste.

---

## 🚀 Installation Rapide (Recommandée)

**Pré-requis :** Raspberry Pi 4 (4GB RAM minimum conseillé), Raspberry Pi OS 64-bit (Lite ou Desktop).
**Système :** `git` et `docker` installés (le script peut installer Docker pour vous).

1.  **Cloner le dépôt :**
    ```bash
    git clone https://github.com/GaspardD78/linkedin-birthday-auto.git
    cd linkedin-birthday-auto
    ```

2.  **Lancer l'installateur :**
    ```bash
    chmod +x setup.sh
    ./setup.sh
    ```
    *Le script gère tout : vérification mémoire/swap, configuration Docker, création certificats SSL temporaires, et lancement des conteneurs.*

3.  **Accéder au Dashboard :**
    *   Ouvrez votre navigateur : `https://<IP_DE_VOTRE_RPI>` (ou le domaine configuré).
    *   Acceptez le certificat auto-signé (si vous n'avez pas encore configuré Let's Encrypt).
    *   Connectez-vous (login par défaut affiché à la fin du script).

---

## 🆕 Nouveautés Jan 2025

Le script setup.sh inclut maintenant plusieurs assistants interactifs pour faciliter l'installation et la sécurité :

### Phase 4.7 : Configuration HTTPS
Pendant le setup, choisissez votre scénario HTTPS :

```
1) LAN uniquement (HTTP simple, réseau interne)
2) Let's Encrypt (production recommandée, certificats automatiques)
3) Certificats existants (import certificats custom)
4) Configuration manuelle (vous gérez après setup)
```

**👉 Guide complet :** [docs/SETUP_HTTPS_GUIDE.md](docs/SETUP_HTTPS_GUIDE.md)

### Phase 5.1 : Sauvegardes Google Drive
Configuration automatisée des backups avec rclone :

```
1) Oui, activer avec chiffrement (recommandé)
2) Oui, activer sans chiffrement
3) Non, configurer plus tard
```

Avantages :
- ✅ Backup quotidien automatique (02:00)
- ✅ Test restore mensuel pour valider intégrité
- ✅ Notifications Slack optionnelles
- ✅ Rétention 30 jours (configurable)

**👉 Guide complet :** [docs/SETUP_BACKUP_GUIDE.md](docs/SETUP_BACKUP_GUIDE.md)

### Rapport Sécurité Automatisé
À la fin du setup, vérification sécurité 4-points :

```
1. Mot de passe Dashboard... ✓ OK (hash bcrypt)
2. HTTPS... ✓ PRODUCTION (Let's Encrypt)
3. Sauvegardes Google Drive... ✓ OK (configurées)
4. Fichier .env secrets... ✓ OK (pas de secrets en clair)

SCORE SÉCURITÉ : 4 / 4
🎉 EXCELLENT - Production Ready
```

### Gestion Mot de Passe Post-Setup
Script dédié pour changer/réinitialiser le mot de passe :

```bash
./scripts/manage_dashboard_password.sh
```

Options :
1. **Changer le mot de passe** - Double saisie + validation
2. **Réinitialiser** - Génère mot de passe temporaire aléatoire
3. **Afficher statut** - Vérifier dernière modification

**👉 Guide complet :** [docs/PASSWORD_MANAGEMENT_GUIDE.md](docs/PASSWORD_MANAGEMENT_GUIDE.md)

---

## 🏗️ Architecture V3.3

Le projet utilise une architecture micro-services sécurisée via Docker Compose :

*   **Bot Worker** (Python/Playwright) : Exécute les tâches d'automatisation dans un environnement isolé.
*   **API** (FastAPI) : Interface de contrôle, communique avec Docker via socket pour gérer les bots.
*   **Dashboard** (Next.js) : Interface utilisateur moderne.
*   **Redis** : File d'attente des tâches et cache.
*   **Nginx** : Reverse Proxy (SSL, Rate Limiting, HTTP/2).
*   **SQLite** : Stockage persistant léger et performant (fichier local).

Pour plus de détails, voir [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## ⚙️ Configuration

La configuration se fait principalement via le fichier `config/config.yaml` ou directement depuis le Dashboard.

**Exemple de config (`config.yaml`) :**
```yaml
bots:
  birthday:
    enabled: true
    mode: "standard" # ou "unlimited"
    schedule: "0 9 * * *" # Cron syntax (9h00 tous les jours)
    messaging:
      template: "Joyeux anniversaire {name} ! 🎉"

  visitor:
    enabled: true
    keywords: ["Recruteur", "CTO", "Tech Lead"]
    location: "Paris"
    limits:
      profiles_per_run: 20
```

---

## 📚 Documentation

### 🆕 Nouvelles Documentations (Jan 2025)

*   [**Quick Start Guide**](docs/QUICK_START_2025.md) : Pour démarrer rapidement (5 min de lecture)
*   [**Guide Configuration HTTPS**](docs/SETUP_HTTPS_GUIDE.md) : Détails sur les 4 options HTTPS + Let's Encrypt
*   [**Guide Sauvegardes Google Drive**](docs/SETUP_BACKUP_GUIDE.md) : Setup rclone, cron, test restore
*   [**Guide Gestion Mot de Passe**](docs/PASSWORD_MANAGEMENT_GUIDE.md) : Change/reset/recover mot de passe
*   [**Troubleshooting Complet**](docs/TROUBLESHOOTING_2025.md) : Solutions pour problèmes courants

### 📖 Documentation Générale

*   [**Résumé Implémentation (Jan 2025)**](docs/IMPLEMENTATION_SUMMARY_2025.md) : Ce qui a été implémenté (statistiques + détails)
*   [**Design Technique (Jan 2025)**](docs/DESIGN_HTTPS_GDRIVE_SECURITY_2025.md) : Architecture détaillée des améliorations
*   [**Analyse Historique (Jan 2025)**](docs/HISTORY_ANALYSIS_2025.md) : Contexte historique + leçons apprises
*   [**Améliorations de Sécurité (Jan 2025)**](docs/SECURITY_ENHANCEMENTS_2025.md) : Corrections critiques implémentées (Grafana, Docker Socket Proxy, Rate Limiting Persistant).
*   [**Améliorations Setup.sh (Jan 2025)**](docs/SETUP_IMPROVEMENTS.md) : Rendre le script idempotent et automatisable.
*   [**Sécurité & Hardening**](docs/SECURITY.md) : Détails sur la protection des données.
*   [**Architecture Technique**](docs/ARCHITECTURE.md) : Pour les développeurs curieux.
*   [**Rapport d'Audit Complet (Jan 2025)**](docs/AUDIT_REPORT_2025-01.md) : Analyse détaillée du code et recommandations.
*   [**Guide de Dépannage (Troubleshooting)**](docs/TROUBLESHOOTING.md) : Problèmes généraux.

---

## 🛠️ Commandes Utiles

**Voir les logs en temps réel :**
```bash
docker compose -f docker-compose.pi4-standalone.yml logs -f
```

**Redémarrer les services :**
```bash
docker compose -f docker-compose.pi4-standalone.yml restart
```

**Mettre à jour le bot :**
```bash
git pull
./setup.sh
```

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Merci d'ouvrir une Issue pour discuter des changements majeurs avant de soumettre une PR.

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---
*Développé avec ❤️ pour la communauté Raspberry Pi.*
