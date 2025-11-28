# 🚫 Fichiers Dépréciés et Nettoyage - État Actuel

Ce document liste l'état des fichiers **dépréciés** dans le repository après le nettoyage du 28 novembre 2025.

> **Date de nettoyage complet :** 28 novembre 2025
> **Version actuelle :** 2.0.0

---

## ✅ Nettoyage Effectué

### Dossiers supprimés

| Dossier | Statut | Date suppression |
|---------|--------|------------------|
| `legacy/` | ✅ SUPPRIMÉ | 28 nov 2025 |
| `.github/workflows/` | ✅ SUPPRIMÉ | 28 nov 2025 |

**Raison** : Ces dossiers contenaient des scripts et configurations obsolètes de la v1.x qui ne sont plus utilisés dans l'architecture v2.0.

---

## 📦 Architecture Actuelle (v2.0)

Le projet utilise maintenant uniquement :

### Structure Moderne

```
linkedin-birthday-auto/
├── main.py                    # ✅ Point d'entrée CLI unifié
├── src/                       # ✅ Code source moderne
│   ├── api/                  # API REST FastAPI
│   ├── bots/                 # Bots (birthday, unlimited)
│   ├── config/               # Configuration Pydantic
│   └── core/                 # Composants core
├── dashboard/                 # ✅ Dashboard Next.js v2
├── scripts/                   # ✅ Scripts de déploiement Pi4
├── config/                    # ✅ Configurations YAML
├── tests/                     # ✅ Tests (unit, integration, e2e)
└── docker-compose.pi4-standalone.yml  # ✅ Docker Compose Pi4
```

### Scripts de Déploiement Actuels

| Script | Description | Statut |
|--------|-------------|--------|
| `scripts/deploy_pi4_standalone.sh` | Déploiement complet Pi4 | ✅ ACTIF |
| `scripts/update_deployment_pi4.sh` | Mise à jour incrémentale | ✅ ACTIF |
| `scripts/cleanup_pi4.sh` | Nettoyage périodique | ✅ ACTIF |
| `scripts/full_cleanup_deployment.sh` | Nettoyage complet | ✅ ACTIF |
| `scripts/verify_rpi_docker.sh` | Vérification déploiement | ✅ ACTIF |
| `scripts/monitor_pi4_resources.sh` | Monitoring ressources | ✅ ACTIF |

---

## 🔄 Migration Complétée

### Ancienne Architecture → Nouvelle Architecture

| Ancien | Nouveau | Statut |
|--------|---------|--------|
| `linkedin_birthday_wisher.py` | `src/bots/birthday_bot.py` + `main.py` | ✅ MIGRÉ |
| `linkedin_birthday_wisher_unlimited.py` | `src/bots/unlimited_bot.py` + `main.py --mode unlimited` | ✅ MIGRÉ |
| `database.py` | `src/core/database.py` | ✅ MIGRÉ |
| `dashboard_app.py` (Flask) | `dashboard/` (Next.js) | ✅ MIGRÉ |
| GitHub Actions workflows | Déploiement local uniquement | ✅ SUPPRIMÉ |
| `legacy/` scripts | Scripts modernes dans `scripts/` | ✅ SUPPRIMÉ |

---

## 📝 Utilisation Actuelle

### Exécution du Bot

**Ancienne méthode (SUPPRIMÉE) :**
```bash
python linkedin_birthday_wisher.py
```

**Nouvelle méthode (ACTIVE) :**
```bash
python main.py bot
# ou
python main.py bot --mode unlimited
# ou avec config YAML
python main.py bot --config config/config.yaml
```

### Déploiement

**Ancienne méthode (SUPPRIMÉE) :**
```bash
# GitHub Actions workflows
gh workflow run main.yml
```

**Nouvelle méthode (ACTIVE) :**
```bash
# Déploiement Pi4 local
./scripts/deploy_pi4_standalone.sh

# Mise à jour
./scripts/update_deployment_pi4.sh

# Nettoyage
./scripts/cleanup_pi4.sh
```

---

## 📊 Statistiques de Nettoyage

| Catégorie | Avant | Après | Économie |
|-----------|-------|-------|----------|
| Dossiers legacy | 1 | 0 | ~206KB |
| GitHub Actions workflows | 1 | 0 | ~11KB |
| Scripts Python root (obsolètes) | 0 | 0 | - |
| Architecture | v1.x + v2.0 | v2.0 uniquement | Simplifié |

---

## 🎯 Recommandations

### Pour les utilisateurs existants

Si vous utilisiez l'ancienne architecture :

1. **Migration obligatoire vers v2.0**
   ```bash
   # Cloner la dernière version
   git pull origin main

   # Utiliser le nouveau point d'entrée
   python main.py bot
   ```

2. **Déploiement Pi4**
   ```bash
   # Nettoyage complet de l'ancien déploiement
   ./scripts/full_cleanup_deployment.sh -y

   # Déploiement nouveau
   ./scripts/deploy_pi4_standalone.sh
   ```

3. **Configuration**
   ```bash
   # Migrer vers config YAML
   cp config/config.yaml config/my_config.yaml
   # Éditer config/my_config.yaml
   ```

---

## 📚 Documentation Mise à Jour

Les documents suivants ont été mis à jour pour refléter l'architecture v2.0 uniquement :

| Document | Statut | Description |
|----------|--------|-------------|
| **[README.md](README.md)** | ✅ À JOUR | Vue d'ensemble v2.0 |
| **[SCRIPTS_USAGE.md](SCRIPTS_USAGE.md)** | ✅ MIS À JOUR | Scripts v2.0 uniquement |
| **[DEPRECATED.md](DEPRECATED.md)** | ✅ MIS À JOUR | Ce document |
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | ✅ À JOUR | Architecture v2.0 |
| **[MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)** | ✅ À JOUR | Migration v1→v2 |

---

## ⚠️ Avertissement

**Les fichiers et dossiers suivants ont été définitivement supprimés** :

- ❌ Dossier `legacy/` complet
- ❌ GitHub Actions workflows (`.github/workflows/`)
- ❌ Scripts Python obsolètes à la racine (déjà supprimés dans versions précédentes)

**Il n'est plus possible de revenir à la v1.x**. Si vous avez besoin de l'ancienne version, consultez l'historique Git :

```bash
# Voir l'historique avant le nettoyage
git log --before="2025-11-28"

# Checkout d'une ancienne version (read-only)
git checkout <commit-hash-avant-nettoyage>
```

---

## 🔍 Support

En cas de problème après le nettoyage :

1. **Documentation** : Consultez [ARCHITECTURE.md](ARCHITECTURE.md) et [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
2. **Scripts** : Voir [SCRIPTS_USAGE.md](SCRIPTS_USAGE.md) pour les nouveaux scripts
3. **Issues GitHub** : [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)

---

## ✅ Résumé

**État après nettoyage :**
- ✅ Projet 100% v2.0
- ✅ Aucun code legacy restant
- ✅ Documentation à jour
- ✅ Scripts de déploiement optimisés pour Pi4
- ✅ Architecture moderne et modulaire

**Prochaines étapes recommandées :**
1. Tester le déploiement avec `./scripts/deploy_pi4_standalone.sh`
2. Vérifier la configuration dans `config/config.yaml`
3. Utiliser `python main.py bot` pour lancer le bot

---

**Dernière mise à jour** : 28 novembre 2025
**Version** : 2.0.0
**Nettoyage complet** : ✅ Terminé
