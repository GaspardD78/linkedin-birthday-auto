# 📦 Fichiers Legacy

Ce dossier contient les **utilitaires legacy** conservés pour compatibilité mais **non maintenus**.

## ⚠️ Avertissement

Ces fichiers :
- ❌ Ne sont **plus maintenus**
- ❌ Peuvent ne **pas fonctionner** avec la version 2.0+
- ❌ Seront **supprimés** dans la version 3.0
- ⚠️ **Utilisez à vos risques et périls**

## 📂 Contenu

| Fichier | Description | Statut |
|---------|-------------|--------|
| `debug_utils.py` | Utilitaires de debug | Remplacé par `src/utils/logging.py` |
| `proxy_manager.py` | Gestion des proxies | Remplacé par `src/config/config_manager.py` |
| `selector_validator.py` | Validation sélecteurs LinkedIn | Outil de debug manuel |
| `visit_profiles.py` | Bot de visite de profils | Feature séparée, à migrer |
| `generate_auth_state.py` | Génération auth state | Voir `RASPBERRY_PI4_GUIDE.md` |
| `generate_auth_simple.py` | Version simplifiée | Doublon de generate_auth_state.py |
| `cleanup_old_logs.py` | Nettoyage logs | Utiliser logrotate |
| `manage_proxy_trials.py` | Gestion essais proxies | Non utilisé (proxy désactivé) |

## 🔄 Migration

### debug_utils.py → src/utils/logging.py

**Avant :**
```python
from debug_utils import setup_logging
setup_logging()
```

**Après :**
```python
from src.utils.logging import get_logger
logger = get_logger(__name__)
```

### proxy_manager.py → config/config.yaml

**Avant :**
```python
from proxy_manager import ProxyManager
pm = ProxyManager()
```

**Après :**
```yaml
# config/config.yaml
proxy:
  enabled: false  # Désactivé pour IP résidentielle Freebox
```

### visit_profiles.py → À migrer

Ce fichier sera migré vers `src/bots/profile_visitor_bot.py` dans une future version.

## 🗓️ Calendrier de Suppression

| Version | Date | Action |
|---------|------|--------|
| v2.0.1 | Nov 2025 | Déplacé dans legacy/ |
| v2.5.0 | Mars 2026 | Avertissement de suppression |
| v3.0.0 | Juin 2026 | **Suppression définitive** |

## 📞 Support

Aucun support n'est fourni pour ces fichiers legacy.

Pour toute question, utilisez les modules modernes dans `src/`.

---

**Date de création :** 22 novembre 2025
**Statut :** ⚠️ NON MAINTENU
