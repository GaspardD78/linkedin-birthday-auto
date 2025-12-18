# Index de la Documentation

Ce fichier recense la documentation technique du projet.
Pour une installation rapide, référez-vous uniquement au `README.md` à la racine.

## 📂 Documentation Générale (`/docs`)

*   **`ARCHITECTURE.md`** : Vue d'ensemble de l'architecture technique (Next.js, Python, Redis, Docker) et flux de données.
*   **`AUTOMATION_DEPLOYMENT_PI4.md`** : Guide détaillé pour le déploiement expert sur Raspberry Pi 4 (référence technique du script `setup.sh`).
*   **`ANTI_INDEXATION_GUIDE.md`** : Explications sur les mesures prises pour empêcher l'indexation du dashboard par les moteurs de recherche.
*   **`BCRYPT_DOCKER_COMPOSE_FIX.md`** : Solution technique pour l'échappement des caractères spéciaux dans les hashs de mots de passe Docker Compose.
*   **`BUGFIX_BROWSER_CRASH_2025_12_10.md`** : Post-mortem et correction d'un bug critique de crash navigateur sur RPi4.
*   **`CONFIGURATION_SERVEUR_HEADLESS.md`** : Guide pour configurer un serveur sans écran (headless), notamment pour l'authentification Google Drive.
*   **`EMAIL_NOTIFICATIONS_INTEGRATION.md`** : Guide d'intégration du système de notifications par email (SMTP).
*   **`FIX_NGINX_GUIDE.md`** : Guide de dépannage pour les configurations Nginx et Reverse Proxy.
*   **`GUIDE_FREEBOX_PORTS.md`** : Tutoriel spécifique pour l'ouverture des ports sur une Freebox.
*   **`MANUAL_HTTPS_SETUP_SUMMARY.md`** : Résumé des étapes pour configurer HTTPS manuellement si le script `setup.sh` échoue.
*   **`NGINX_RATE_LIMIT_FIX.md`** : Détails sur la configuration du rate limiting Nginx pour éviter les blocages.
*   **`OVERVIEW_PAGE.md`** : Description des fonctionnalités de la page "Vue d'ensemble" du dashboard.
*   **`RASPBERRY_PI_TROUBLESHOOTING.md`** : Guide de dépannage spécifique aux problèmes matériels et système du Raspberry Pi 4 (Swap, Température, Mémoire).
*   **`RCLONE_DOCKER_AUTH_GUIDE.md`** : Guide pour l'authentification rclone (Google Drive) dans un environnement Docker.
*   **`README.md`** : (Fichier interne au dossier docs) Documentation historique ou spécifique au dossier.
*   **`UPDATE_GUIDE.md`** : Procédure manuelle de mise à jour (automatisée par `setup.sh`).
*   **`USB_STORAGE_OPTIMIZATION.md`** : Guide pour optimiser les performances en utilisant un stockage USB/SSD sur RPi4.
*   **`VERIFY_SECURITY_GUIDE.md`** : Liste des points de contrôle de sécurité vérifiés par les scripts d'audit.

## 🗄️ Archives (`_ARCHIVE_2025/`)

Les anciens guides, plans de migration et rapports d'audit ont été déplacés dans ce dossier pour alléger la racine du projet. Ils ne sont conservés qu'à titre historique.
