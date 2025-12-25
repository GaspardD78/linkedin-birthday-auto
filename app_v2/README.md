# 🧪 LinkedIn Auto Bot V2 (Experimental)

**Status:** 🚧 Work In Progress / Beta
**Architecture:** Async-First (FastAPI + SQLAlchemy Async + Playwright)

---

## ⚠️ Avertissement

Cette version (**app_v2**) est une refonte majeure de l'application. Elle n'est **PAS** encore prête pour la production.
Veuillez utiliser la version stable située dans le dossier `src/` (documentée dans le [README principal](../README.md)) pour tout déploiement réel.

---

## 🌟 Objectifs de la V2

L'objectif de cette version est de moderniser l'architecture pour résoudre les limitations de la V1 :

*   **Performance :** Architecture 100% asynchrone pour gérer plus de tâches simultanées.
*   **Scalabilité :** Meilleure séparation des services (API, Worker, DB).
*   **Maintenance :** Codebase plus modulaire suivant les principes SOLID.
*   **API-First :** Design piloté par l'API pour faciliter l'intégration du Dashboard.

## 🏗️ Architecture Technique

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI (Main.py)                     │
├─────────────────────────────────────────────────────────┤
│ API Layer (routers: control, data)                      │
├─────────────────────────────────────────────────────────┤
│ Service Layer (BirthdayService, VisitorService)         │
├─────────────────────────────────────────────────────────┤
│ Engine Layer (AuthManager, ActionManager, Selectors)    │
├─────────────────────────────────────────────────────────┤
│ Database Layer (SQLAlchemy async + SQLite)              │
└─────────────────────────────────────────────────────────┘
```

## 🛠️ État d'Avancement (Décembre 2025)

Basé sur le [Rapport d'Analyse](../docs/audit/APP_V2_ANALYSIS_REPORT.md).

| Composant | État | Notes |
|-----------|------|-------|
| **Architecture** | ⭐⭐⭐⭐ | Design solide et moderne. |
| **Fonctionnalités** | ⭐⭐⭐ | Bots Anniversaire et Visiteur implémentés. |
| **Sécurité** | ⭐⭐ | **CRITIQUE** : Manque d'authentification sur les routes API. |
| **Tests** | ⭐ | Aucun test unitaire présent. |
| **Stabilité** | ⭐⭐ | Race conditions identifiées dans la gestion des quotas. |

## 🚀 Comment Tester (Développeurs Uniquement)

**Pré-requis :** Python 3.11+, Poetry ou Pipenv.

1.  **Installer les dépendances :**
    ```bash
    pip install -r requirements-v2.txt  # (À créer si inexistant)
    # ou
    poetry install
    ```

2.  **Configuration :**
    Copier `.env.example` vers `.env` et configurer les clés.

3.  **Lancer l'API :**
    ```bash
    uvicorn app_v2.main:app --reload
    ```

## 📝 Roadmap vers la Production

Pour passer cette version en production, les chantiers suivants sont prioritaires :

1.  🔴 **Sécurité :** Implémenter l'authentification (JWT/API Key) sur tous les endpoints.
2.  🔴 **Tests :** Écrire une suite de tests unitaires et d'intégration (couverture > 80%).
3.  🔴 **Concurrence :** Fixer les race conditions (verrous DB) pour les quotas.
4.  🟠 **Robustesse :** Améliorer la résilience des sélecteurs CSS (Smart Selectors).

---

**Note :** Pour toute contribution, merci de se référer au dossier `docs/` et aux rapports d'audit.
