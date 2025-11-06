# Changelog - LinkedIn Birthday Bot

## Version 1.1.1 - Correctif Modules ES6 (2025-11-06)

### 🐛 Correctifs Critiques

- **Correction des modules ES6 dans content.js** : Les content scripts Chrome ne supportent pas nativement les imports ES6. Le code a été converti en JavaScript classique avec toutes les fonctions inline.
- **Manifest.json simplifié** : Retrait des références inutiles aux fichiers modules séparés
- **Extension maintenant fonctionnelle** : Plus d'erreurs "Cannot use import statement outside a module"

**Note technique** : popup.js et settings.js continuent d'utiliser les modules ES6 (constants.js et utils.js) car ils sont chargés via des pages HTML avec `type="module"`, ce qui est supporté. Seul content.js a été converti en standalone.

---

## Version 1.1.0 - Améliorations Majeures

### ✨ Nouvelles Fonctionnalités

#### **Architecture**
- ✅ Création de `constants.js` pour centraliser toutes les constantes
- ✅ Création de `utils.js` avec fonctions utilitaires réutilisables
- ✅ Support des modules ES6 dans toute l'extension
- ✅ Code bien structuré et documenté avec JSDoc

#### **Système de Tracking**
- ✅ Historique des messages envoyés
- ✅ Prévention des doublons (pas de double envoi le même jour)
- ✅ Nettoyage automatique de l'historique (garde 7 jours)
- ✅ Indication visuelle des contacts déjà contactés

#### **Barre de Progression**
- ✅ Barre de progression fonctionnelle pendant l'envoi
- ✅ Affichage en temps réel du nombre de messages envoyés
- ✅ Pourcentage de progression
- ✅ Communication bidirectionnelle entre content.js et popup.js

### 🐛 Corrections de Bugs

#### **content.js**
- ✅ Élimination du code dupliqué (extraction de nom)
- ✅ Meilleure gestion d'erreurs avec try-catch
- ✅ Logging structuré pour faciliter le debug
- ✅ Gestion des messages ignorés (skipped)

#### **popup.js**
- ✅ Code moderne avec async/await (exit callback hell)
- ✅ Meilleure gestion d'erreurs
- ✅ État géré proprement avec variables locales
- ✅ Auto-scan au chargement fonctionnel

#### **settings.js**
- ✅ Élimination de la fonction globale `removeTemplate()`
- ✅ Utilisation d'event listeners au lieu de onclick inline
- ✅ Validation en temps réel des templates
- ✅ Meilleure UX avec messages d'erreur clairs

### 🎨 Améliorations UI/UX

#### **Validation des Templates**
- ✅ Vérification que `{prenom}` est présent
- ✅ Validation de la longueur (10-500 caractères)
- ✅ Feedback visuel en temps réel (bordures colorées)
- ✅ Messages d'erreur explicites

#### **Liste des Anniversaires**
- ✅ Indication visuelle (✅) pour les messages déjà envoyés
- ✅ Opacité réduite pour les contacts déjà contactés
- ✅ Compteur des contacts à traiter
- ✅ Désactivation automatique du bouton si tous envoyés

#### **Statistiques**
- ✅ Formatage des nombres (1 000 au lieu de 1000)
- ✅ Formatage des dates en français
- ✅ Reset des stats avec confirmation

### 🔧 Améliorations Techniques

#### **Sélecteurs DOM Améliorés**
- ✅ Sélecteurs multiples par ordre de priorité
- ✅ Fallback sur plusieurs stratégies
- ✅ Logging des sélecteurs qui fonctionnent
- ✅ Plus stable face aux changements de LinkedIn

#### **Gestion des Erreurs**
- ✅ Try-catch sur toutes les opérations critiques
- ✅ Messages d'erreur utilisateur-friendly
- ✅ Logging détaillé pour le debug
- ✅ Gestion des timeouts et erreurs réseau

#### **Performance**
- ✅ Chargement parallèle des ressources (Promise.all)
- ✅ Délais aléatoires entre envois (3-6 secondes)
- ✅ Code plus léger et mieux organisé

### 📝 Documentation

- ✅ Commentaires JSDoc sur toutes les fonctions
- ✅ Code auto-documenté avec noms explicites
- ✅ Sections clairement délimitées
- ✅ Ce fichier CHANGELOG.md

### 🔒 Sécurité & Bonnes Pratiques

- ✅ Validation de toutes les entrées utilisateur
- ✅ Échappement des caractères spéciaux
- ✅ Pas de `eval()` ou code dangereux
- ✅ Respect des bonnes pratiques Chrome Extension

## Fichiers Modifiés

### Nouveaux Fichiers
- `constants.js` - Constantes globales
- `utils.js` - Fonctions utilitaires
- `CHANGELOG.md` - Ce fichier

### Fichiers Refactorisés
- `content.js` - Refactorisation complète (234 → 345 lignes, mais mieux structuré)
- `popup.js` - Refactorisation complète (171 → 418 lignes avec barre de progression)
- `settings.js` - Refactorisation complète (112 → 354 lignes avec validation)
- `manifest.json` - Ajout des nouveaux fichiers et web_accessible_resources
- `popup.html` - Type module
- `settings.html` - Type module + styles validation

## Migration

L'extension est rétro-compatible. Les utilisateurs existants verront simplement les nouvelles fonctionnalités sans perte de données.

## Performance

### Avant
- Code dupliqué
- Pas de tracking
- Barre de progression non fonctionnelle
- Erreurs mal gérées

### Après
- Code DRY (Don't Repeat Yourself)
- Tracking complet avec historique
- Barre de progression en temps réel
- Gestion complète des erreurs

## Prochaines Améliorations Possibles

1. Mode preview avant envoi
2. Sélection individuelle des contacts
3. Templates avec plus de variables ({nom_complet}, {entreprise}, etc.)
4. Statistiques avancées (graphiques)
5. Export des statistiques
6. Tests unitaires
7. CI/CD avec GitHub Actions

---

**Version précédente** : 1.0.0
**Version actuelle** : 1.1.0
**Date** : 2025-11-06
**Développeur** : Améliorations par Claude Code
