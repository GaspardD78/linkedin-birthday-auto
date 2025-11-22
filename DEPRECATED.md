# 🚫 Fichiers Dépréciés

Ce document liste les fichiers **dépréciés** dans le repository qui seront **supprimés dans la version 3.0**.

> **Date de dépréciation :** 22 novembre 2025
> **Suppression prévue :** Version 3.0 (Q1 2026)

---

## ⚠️ Fichiers Python Legacy (Root Level)

Les fichiers suivants sont **dépréciés** et remplacés par l'architecture moderne dans `src/`.

| Fichier | Statut | Remplacement | Action |
|---------|--------|--------------|--------|
| `linkedin_birthday_wisher.py` | ⛔ DEPRECATED | `src/bots/birthday_bot.py` + `main.py` | ❌ NE PLUS UTILISER |
| `linkedin_birthday_wisher_unlimited.py` | ⛔ DEPRECATED | `src/bots/unlimited_bot.py` + `main.py --mode unlimited` | ❌ NE PLUS UTILISER |
| `database.py` | ⛔ DEPRECATED | `src/core/database.py` | ❌ NE PLUS UTILISER |
| `dashboard_app.py` | ⛔ DEPRECATED | `dashboard/` (Next.js) ou FastAPI (`src/api/app.py`) | ❌ NE PLUS UTILISER |
| `debug_utils.py` | ⚠️ LEGACY | `src/utils/logging.py` | Utiliser avec précaution |
| `proxy_manager.py` | ⚠️ LEGACY | `src/config/config_manager.py` (proxy config) | Utiliser avec précaution |
| `selector_validator.py` | ⚠️ LEGACY | Validation manuelle | Outil de debug |
| `visit_profiles.py` | ⚠️ SEPARATE FEATURE | Fonctionnalité indépendante | À migrer vers `src/bots/` |

### Migration vers src/

**Ancienne méthode (DEPRECATED) :**
```bash
python linkedin_birthday_wisher.py
```

**Nouvelle méthode (RECOMMANDÉE) :**
```bash
python main.py
# ou
python main.py --mode unlimited
# ou avec config YAML
python main.py --config config/config.yaml
```

---

## 🧪 Fichiers de Tests Obsolètes

Ces fichiers de tests ne sont **plus maintenus** et doivent être migrés vers `tests/`.

| Fichier | Statut | Action |
|---------|--------|--------|
| `test_phase1.py` | ⛔ OBSOLETE | Supprimer ou migrer vers `tests/integration/` |
| `test_birthday_detection.py` | ⛔ OBSOLETE | Supprimer ou migrer vers `tests/unit/` |
| `test_birthday_detection_real.py` | ⛔ OBSOLETE | Supprimer ou migrer vers `tests/e2e/` |

**Action recommandée :** Migrer les tests pertinents vers `tests/unit/` ou `tests/integration/`.

---

## 📄 Fichiers de Debug à Supprimer

Ces fichiers de debug ne devraient **pas** être dans le repository :

| Fichier | Taille | Statut | Action |
|---------|--------|--------|--------|
| `birthdays_page.html` | 939 KB | ⛔ DEBUG ARTIFACT | ❌ Supprimer |
| `birthdays_page.png` | 130 KB | ⛔ DEBUG ARTIFACT | ❌ Supprimer |
| `error_unexpected.png` | 4.5 KB | ⛔ DEBUG ARTIFACT | ❌ Supprimer |
| `content.js` | 19 KB | ⛔ OBSOLETE | ❌ Supprimer |
| `visited_profiles.txt` | - | ⛔ DATA FILE | ❌ Supprimer |

**Action :** Ces fichiers ont été ajoutés au `.gitignore` et seront supprimés lors du prochain nettoyage.

---

## 📦 Fichiers de Configuration Dupliqués

| Fichier | Statut | Remplacement | Action |
|---------|--------|--------------|--------|
| `requirements.txt` | ⚠️ OLD | `requirements-new.txt` | ✅ Utiliser `requirements-new.txt` |
| `config.json` | ⚠️ LEGACY FORMAT | `config/config.yaml` | ✅ Migrer vers YAML |

### Migration des Requirements

**Ancienne méthode :**
```bash
pip install -r requirements.txt
```

**Nouvelle méthode (RECOMMANDÉE) :**
```bash
pip install -r requirements-new.txt
```

---

## 🔧 Utilitaires à Migrer

Ces utilitaires sont fonctionnels mais doivent être intégrés dans `src/utils/` :

| Fichier | Statut | Action Recommandée |
|---------|--------|-------------------|
| `generate_auth_state.py` | ⚠️ STANDALONE | Migrer vers `src/cli/` ou `src/utils/` |
| `generate_auth_simple.py` | ⚠️ DUPLICATE | Fusionner avec `generate_auth_state.py` |
| `cleanup_old_logs.py` | ⚠️ STANDALONE | Migrer vers `src/utils/maintenance.py` |
| `manage_proxy_trials.py` | ⚠️ LEGACY | Supprimer (proxies non utilisés sur Pi 4) |

---

## 📱 Dashboards Dupliqués

### ⛔ Flask Dashboard (DEPRECATED)

**Fichier :** `dashboard_app.py` (898 lignes)
**Statut :** ⛔ DEPRECATED

**Raisons de la dépréciation :**
- Architecture monolithique (tout dans un fichier)
- Dépendance Flask vs FastAPI (utilisé ailleurs)
- Dashboard Next.js moderne plus performant
- Consomme plus de RAM sur Pi 4

**Remplacement :**
```bash
# Ancien (Flask)
python dashboard_app.py

# Nouveau (Next.js)
cd dashboard
npm run build
npm start

# OU FastAPI (pour API REST)
uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

---

## ⏱️ Calendrier de Suppression

| Version | Date Prévue | Actions |
|---------|-------------|---------|
| **v2.0.1** | ✅ Nov 2025 | Marquage deprecated, avertissements |
| **v2.1.0** | ⚠️ Dec 2025 | Migration obligatoire vers `src/` |
| **v2.2.0** | 📅 Jan 2026 | Suppression des warnings |
| **v3.0.0** | 🗑️ Q1 2026 | **SUPPRESSION DÉFINITIVE** |

---

## 📚 Guide de Migration

### Étape 1 : Vérifier que vous utilisez la nouvelle architecture

```bash
# Vérifier que main.py fonctionne
python main.py --help

# Tester en mode dry-run
python main.py --dry-run
```

### Étape 2 : Migrer votre configuration

```bash
# Copier votre ancien .env
cp .env .env.backup

# Créer config.yaml basé sur config/config.yaml
cp config/config.yaml config/my_config.yaml
# Éditer config/my_config.yaml avec vos paramètres
```

### Étape 3 : Tester la nouvelle version

```bash
# Lancer avec la nouvelle config
python main.py --config config/my_config.yaml --dry-run

# Vérifier les logs
tail -f logs/linkedin_bot.log
```

### Étape 4 : Supprimer les anciens fichiers (optionnel)

```bash
# Créer un backup avant suppression
mkdir -p backup_legacy
mv linkedin_birthday_wisher*.py backup_legacy/
mv database.py backup_legacy/
mv dashboard_app.py backup_legacy/
```

---

## ❓ Questions Fréquentes

### Q: Puis-je encore utiliser les anciens scripts ?

**R:** Oui, ils fonctionnent encore en v2.0.1, mais :
- ⚠️ Pas de corrections de bugs
- ⚠️ Pas de nouvelles fonctionnalités
- ⛔ Suppression en v3.0.0

### Q: Comment migrer mes données ?

**R:** La base de données est compatible entre anciennes et nouvelles versions :
```bash
# Ancienne DB: linkedin_birthday.db
# Nouvelle DB: linkedin_automation.db

# Migration automatique lors du premier lancement
python main.py
```

### Q: Et si j'ai des modifications personnalisées ?

**R:**
1. Créer une issue GitHub avec vos modifications
2. Nous intégrerons les fonctionnalités utiles dans `src/`
3. Ou créer un bot personnalisé en héritant de `BaseLinkedInBot`

---

## 📞 Support

En cas de problème avec la migration :

1. **Documentation :** Consultez [ARCHITECTURE.md](ARCHITECTURE.md) et [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
2. **Issues GitHub :** [github.com/GaspardD78/linkedin-birthday-auto/issues](https://github.com/GaspardD78/linkedin-birthday-auto/issues)
3. **Exemples :** Voir `main_example.py` pour des exemples d'utilisation

---

**Date de mise à jour :** 22 novembre 2025
**Version du document :** 1.0
