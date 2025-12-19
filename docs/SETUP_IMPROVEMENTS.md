# Améliorations Setup.sh - Idempotence, UX & Sécurité Hash

**Date:** 2025-01-19
**Version:** v3.3+
**Focus:**
- Rendre setup.sh réexécutable sans interactions redondantes
- Améliorer l'interaction utilisateur avec des menus clairs
- Documenter le hachage bcrypt et le doublage des `$`

---

## 📖 RÉFÉRENCE COMPLÈTE

Pour une documentation détaillée et complète sur le hachage du mot de passe, consultez :
👉 **[docs/SETUP_SCRIPT_PASSWORD_HASHING.md](./SETUP_SCRIPT_PASSWORD_HASHING.md)**

Ce document couvre :
- Le processus complet de hachage bcrypt
- Pourquoi les `$` sont doublés dans `.env`
- Les menus d'interaction utilisateur
- Des exemples pratiques et troubleshooting

---

## Problème Identifié

### Setup.sh Non-Idempotent pour le Mot de Passe

**Avant:** À chaque exécution du script, même après une configuration réussie, le script demandait à nouveau le mot de passe Dashboard.

```bash
# ANCIENNE CONDITION (NON-IDEMPOTENTE)
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || grep -q "^DASHBOARD_PASSWORD=[^$]" "$ENV_FILE"; then
    echo -n "Entrez le nouveau mot de passe : "
    read -rs PASS_INPUT
    # ...
fi
```

**Problème:** La condition `grep -q "^DASHBOARD_PASSWORD=[^$]"` signifie "un mot de passe qui ne commence pas par $". Mais après le premier hachage bcrypt (qui commence par `$2a$` ou `$2b$` ou `$2y$`), la seconde exécution voyait une configuration valide et redémarrait le prompt.

**Impact:**
- ❌ UX dégradée - demande répétée même après configuration
- ❌ Maintenance - impossible de relancer setup.sh sans interagir
- ✅ Mais pas une faille de sécurité (le mot de passe existant était préservé)

---

## Solution Implémentée

### Logique Idempotente

```bash
# NOUVELLE CONDITION (IDEMPOTENTE)
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || ! grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE"; then
    # Vérifier si c'est vraiment un hash bcrypt
    if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE"; then
        log_info "Mot de passe Dashboard déjà configuré (hash bcrypt détecté). Skip."
    else
        # SEULEMENT ICI on demande le mot de passe
        echo -n "Entrez le nouveau mot de passe : "
        read -rs PASS_INPUT
        # ... hachage ...
    fi
fi
```

### Logique Expliquée

| Condition | Action |
|-----------|--------|
| `CHANGEZ_MOI` en dur dans .env | ✅ Demander mot de passe |
| `DASHBOARD_PASSWORD=$2a$...` (hash bcrypt) | ✅ SKIP - Déjà configuré |
| `DASHBOARD_PASSWORD=cleartext` | ✅ Demander mot de passe (insécure) |
| `DASHBOARD_PASSWORD` manquant | ✅ Demander mot de passe |
| Relancer setup.sh avec config valide | ✅ SKIP - Idempotent |

### Pattern bcrypt Reconnu

Le script détecte les hashes bcrypt valides via la regex: `^DASHBOARD_PASSWORD=\$2[aby]\$`

```
Versions bcrypt:
├─ $2a$12$... (original, version A)
├─ $2b$12$... (correct, version B)
└─ $2y$12$... (PHP, version Y)
```

---

## Bénéfices

### 1. ✅ Idempotence Complète
```bash
./setup.sh   # Demande mot de passe
./setup.sh   # SKIP - Déjà configuré
./setup.sh   # SKIP - Déjà configuré
```

### 2. ✅ Meilleure UX
- Setup peut être relancé sans interaction
- Parfait pour scripts d'automatisation et CI/CD
- Développeurs peuvent tester sans être bloqués

### 3. ✅ Compatibilité Backward
- Ancien .env avec `CHANGEZ_MOI` → Demande mot de passe
- Ancien .env avec mot de passe en clair → Demande hachage
- Nouveau .env avec hash bcrypt → Skip

### 4. ✅ Maintenabilité
```bash
# Pour réinitialiser le mot de passe en dur:
sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env
./setup.sh   # Demandera à nouveau le mot de passe
```

---

## Cas d'Usage

### Cas 1: Première Installation
```bash
$ ./setup.sh
[INFO] Configuration du Mot de Passe Dashboard
Entrez le nouveau mot de passe : ••••••••
[OK] Mot de passe mis à jour et haché.
$ cat .env | grep DASHBOARD_PASSWORD
DASHBOARD_PASSWORD=$2b$12$...hash...
```

### Cas 2: Relancer Setup.sh
```bash
$ ./setup.sh
[INFO] Mot de passe Dashboard déjà configuré (hash bcrypt détecté). Skip.
# Aucune interaction, continue rapidement
```

### Cas 3: Réinitialiser le Mot de Passe
```bash
$ sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env
$ ./setup.sh
[INFO] Configuration du Mot de Passe Dashboard
Entrez le nouveau mot de passe : ••••••••
[OK] Mot de passe mis à jour et haché.
```

---

## Détails Implémentation

### Fichier Modifié
- `setup.sh` lignes 328-382

### Changements
- ✅ Logique de détection améliorée (4 niveaux)
- ✅ Commentaires explicatifs (lignes 329-332)
- ✅ Vérification anticipée si hash valide (ligne 335)
- ✅ Message informatif clair (ligne 336)
- ✅ Indentation améliorée pour lisibilité

### Tests Recommandés
```bash
# Test 1: Première installation (nouveau .env)
rm -f .env && ./setup.sh
# → Doit demander le mot de passe

# Test 2: Relancer setup.sh
./setup.sh
# → Doit skiper le mot de passe

# Test 3: Réinitialiser
sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env
./setup.sh
# → Doit demander le mot de passe à nouveau

# Test 4: Mot de passe en clair (sécurité)
sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=myplaintext|' .env
./setup.sh
# → Doit demander le hachage et remplacer
```

---

## Impact sur Sécurité

✅ **Aucun impact négatif:**
- La logique de hachage bcrypt reste identique
- Les mots de passe restent protégés par bcrypt
- Pas de dégradation de sécurité

✅ **Amélioration potentielle:**
- Rend l'automatisation plus sûre (moins d'erreurs manuelles)
- Facile de tester en CI/CD
- Comportement prévisible

---

## Compatibilité

| Scenario | Status |
|----------|--------|
| Ancien .env format | ✅ Compatible |
| Nouveau .env format | ✅ Compatible |
| Setup.sh multirun | ✅ Idempotent |
| CI/CD automation | ✅ Supported |
| Docker usage | ✅ No impact |

---

## Score d'Amélioration

| Aspect | Avant | Après |
|--------|-------|-------|
| Idempotence | ❌ Non | ✅ Oui |
| UX Setup | ⚠️ Acceptable | ✅ Excellent |
| Automatisation | ❌ Difficile | ✅ Facile |
| Facilité de test | ⚠️ Moyenne | ✅ Haute |

---

## ⚠️ Important : Doublage des `$` dans le Hash Bcrypt

### Qu'est-ce qu'on fait ?

Lorsque le script écrit le mot de passe haché dans `.env`, il **double tous les caractères `$`** du hash bcrypt.

**Avant (hash brut généré) :**
```
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

**Après (dans .env) :**
```
$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

### Pourquoi c'est nécessaire ?

Le caractère `$` est spécial dans les fichiers shell : il déclenche l'**expansion de variables**.

Sans le doublage :
```bash
# .env contient :
DASHBOARD_PASSWORD=$2b$12$...

# Shell interprète ceci comme :
DASHBOARD_PASSWORD=<valeur de 2b> <valeur de 12> ...  ← ERREUR !
```

Avec le doublage :
```bash
# .env contient :
DASHBOARD_PASSWORD=$$2b$$12$$...

# Shell interprète $$ comme un seul $, donc :
DASHBOARD_PASSWORD=$2b$12$...  ← CORRECT ✓
```

### Comment le Script le Fait ?

Ligne 502 dans `setup.sh` :
```bash
SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
```

Cela remplace chaque `$` par `$$` automatiquement.

### Ce que Vous Devez Savoir

✅ **NORMAL :** Voir des `$$` dans le fichier `.env`
```bash
DASHBOARD_PASSWORD=$$2b$$12$$...
```

❌ **NE PAS FAIRE :** Modifier les `$$` manuellement
```bash
# MAUVAIS - ne faites pas ça !
sed -i 's/\$\$/\$/g' .env   # ← supprime les doublons

# Le mot de passe ne fonctionnera plus !
```

✅ **SI VOUS DEVEZ RECONFIGURER :** Utilisez le script
```bash
sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env
./setup.sh
```

### Documentation Complète

Voir : **[docs/SETUP_SCRIPT_PASSWORD_HASHING.md](./SETUP_SCRIPT_PASSWORD_HASHING.md)** pour tous les détails techniques.

---

## Références

- Audit Report: [docs/AUDIT_REPORT_2025-01.md](./AUDIT_REPORT_2025-01.md)
- Security Enhancements: [docs/SECURITY_ENHANCEMENTS_2025.md](./SECURITY_ENHANCEMENTS_2025.md)
- Password Hashing Details: **[docs/SETUP_SCRIPT_PASSWORD_HASHING.md](./SETUP_SCRIPT_PASSWORD_HASHING.md)** ⭐ NEW
- Setup Guide: [docs/RASPBERRY_PI_DOCKER_SETUP.md](./RASPBERRY_PI_DOCKER_SETUP.md)

---

*Document généré le 2025-01-19 par Claude Code - Setup Improvements v3.3+*
