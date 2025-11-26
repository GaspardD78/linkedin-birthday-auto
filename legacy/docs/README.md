# 📚 Documentation Archivée (Legacy)

Cette documentation est **archivée** car elle concerne des configurations obsolètes ou qui ne sont plus utilisées dans le setup actuel.

## 📋 Fichiers Archivés

### SETUP_PI4_SYNOLOGY_FREEBOX.md
**Raison :** Configuration avec NAS Synology DS213J obsolète
**Remplacé par :** `SETUP_PI4_FREEBOX.md` (setup standalone à la racine)
**Date d'archivage :** Novembre 2025

L'architecture actuelle utilise uniquement le Raspberry Pi 4 en mode standalone avec SQLite, sans dépendance au NAS Synology.

### PROXY_FREE_TRIALS_GUIDE.md
**Raison :** Guide pour proxies premium non nécessaire
**Remplacé par :** Utilisation de l'IP résidentielle de la Freebox Pop
**Date d'archivage :** Novembre 2025

Le setup actuel sur Raspberry Pi 4 utilise l'IP résidentielle directement via la Freebox, éliminant le besoin de proxies payants.

### REVERSE_PROXY.md
**Raison :** Configuration spécifique au reverse proxy Synology
**Remplacé par :** Accès direct via Freebox ou configuration manuelle
**Date d'archivage :** Novembre 2025

Sans le NAS Synology, ce guide n'est plus pertinent pour le setup standalone.

---

## 🔄 Migration vers la Documentation Actuelle

Si vous cherchez à configurer le bot, consultez plutôt :

- **Guide principal de setup :** `SETUP_PI4_FREEBOX.md` (à la racine)
- **Architecture v2 :** `ARCHITECTURE.md` (à la racine)
- **Documentation technique :** Dossier `docs/` (à la racine)

---

## 💡 Note

Ces documents sont conservés à titre de référence historique et peuvent contenir des informations utiles pour d'autres configurations, mais ne sont **pas maintenus** et peuvent contenir des informations obsolètes.

**Date de mise à jour :** Novembre 2025
