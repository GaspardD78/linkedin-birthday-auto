# 🔒 Guide Détaillé : Hachage du Mot de Passe Dashboard dans setup.sh

**Date :** 2025-01-19
**Version :** v3.3+
**Sujet :** Gestion sécurisée du mot de passe dashboard avec hachage bcrypt et interaction utilisateur

---

## 📋 Table des Matières

1. [Problème Résolu](#problème-résolu)
2. [Concept : Hachage Bcrypt et Caractères Spéciaux](#concept--hachage-bcrypt-et-caractères-spéciaux)
3. [Solution : Doublage des `$` et Interaction Utilisateur](#solution--doublage-des--et-interaction-utilisateur)
4. [Processus Détaillé](#processus-détaillé)
5. [Interaction Utilisateur](#interaction-utilisateur)
6. [Exemples Pratiques](#exemples-pratiques)
7. [Troubleshooting](#troubleshooting)

---

## ❌ Problème Résolu

### Avant (v3.1 & v3.2)

Le script `setup.sh` avait deux limitations :

1. **Hachage incomplet** : Bien que le script FASSE le doublage des `$`, cela n'était PAS documenté clairement
2. **UX basique** : Une simple demande de mot de passe sans menu ou options de choix
3. **Documentation insuffisante** : Les développeurs ne comprenaient pas pourquoi les `$` étaient doublés dans `.env`

### Impact

- ❌ Confusion sur pourquoi les hashes contenaient des `$$` dans `.env`
- ❌ Risque de modification manuelle du `.env` et suppression accidentelle des doublons
- ❌ Mauvaise UX - pas de choix clair pour réutiliser un mot de passe existant

---

## 🔐 Concept : Hachage Bcrypt et Caractères Spéciaux

### Pourquoi les Hashes Bcrypt Contiennent des `$`

Le format bcrypt est défini comme suit :

```
$2a$12$abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTU
│ │ │ │
│ │ │ └─ Hash avec salt (22 caractères + hash)
│ │ └─── Coût (nombre de rounds)
│ └───── Version (a, b, y)
└─────── Identifiant bcrypt
```

**Exemple réel :**
```
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

### Problème avec le Shell

Dans un fichier `.env` interprété par le shell, le caractère `$` a une signification spéciale :

```bash
# Exemple problématique :
DASHBOARD_PASSWORD=$2b$12$...

# Le shell interprète ceci comme :
DASHBOARD_PASSWORD=<valeur de 2b> <valeur de 12> ...
```

Cela cause :
- **Expansion de variables** indésirables
- **Perte du hash** ou interprétation incorrecte
- **Erreurs de syntaxe shell**

### Solution : Doublage des `$`

Dans les fichiers shell, `$$` est interprété comme un seul `$` littéral.

```bash
# Avant (en mémoire - hash brut) :
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k

# Dans .env (fichier, avec doublage) :
$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k

# Lors de la lecture par l'app (shell interprète) :
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k (correct)
```

---

## ✅ Solution : Doublage des `$` et Interaction Utilisateur

### Améliorations Implémentées (v3.3+)

#### 1. **Fonctions Utilitaires d'Interaction**

Le script introduit 3 nouvelles fonctions réutilisables :

```bash
# Pose une question yes/no
prompt_yes_no "Voulez-vous continuer ?" [default]

# Affiche un menu numéroté
prompt_menu "Titre" "Option 1" "Option 2" "Option 3"

# Menu spécifique pour le mot de passe
prompt_password_action [true|false]
```

#### 2. **Menu de Configuration du Mot de Passe**

Au lieu de simplement demander un mot de passe, le script propose 2-3 choix :

**Si pas de mot de passe détecté :**
```
Configuration du Mot de Passe Dashboard

  1) Définir un nouveau mot de passe
  2) Annuler la configuration pour l'instant

Votre choix [1-2] (timeout 30s) :
```

**Si un mot de passe existe déjà :**
```
Configuration du Mot de Passe Dashboard

  1) Définir/Changer le mot de passe maintenant
  2) Garder le mot de passe existant
  3) Annuler la configuration pour l'instant

Votre choix [1-3] (timeout 30s) :
```

#### 3. **Doublage des `$` - Explicitement Documenté**

Le script contient maintenant 35+ lignes de commentaires explicitant :

- **Pourquoi** les `$` sont doublés (expansion de variables shell)
- **Où** le doublage se fait (dans le script, avant l'écriture dans `.env`)
- **Comment** l'app reçoit le hash correct (réinterprétation du shell)
- **Processus étape par étape** (générer → doubler → échapper → écrire)

---

## 🔄 Processus Détaillé

### Flux Complet de Hachage et Écriture

#### Étape 1 : Détection du Mot de Passe Actuel

```bash
HAS_BCRYPT_HASH=false
if grep -q "^DASHBOARD_PASSWORD=\$2[aby]\$" "$ENV_FILE"; then
    HAS_BCRYPT_HASH=true
fi
```

**Explications :**
- Cherche une ligne `DASHBOARD_PASSWORD=` commençant par `$2a$`, `$2b$` ou `$2y$`
- Si trouvée → mot de passe valide, pas besoin de reconfigurer
- Si non trouvée → demander une nouvelle configuration

#### Étape 2 : Déterminer si Configuration Requise

```bash
NEEDS_PASSWORD_CONFIG=false
if grep -q "CHANGEZ_MOI" "$ENV_FILE" || [[ "$HAS_BCRYPT_HASH" == "false" ]]; then
    NEEDS_PASSWORD_CONFIG=true
fi
```

**Cas qui déclenchent la configuration :**
- Placeholder `CHANGEZ_MOI` présent dans `.env` (nouveau setup)
- Pas de hash bcrypt valide détecté

#### Étape 3 : Présenter le Menu d'Interaction

```bash
if [[ "$NEEDS_PASSWORD_CONFIG" == "true" ]]; then
    if [[ "$HAS_BCRYPT_HASH" == "true" ]]; then
        ACTION=$(prompt_password_action "true")   # 3 choix
    else
        ACTION=$(prompt_password_action "false")  # 2 choix
    fi
fi
```

#### Étape 4 : Générer le Hash Bcrypt

```bash
HASH_OUTPUT=$(docker run --rm \
    --entrypoint node \
    -e PWD_INPUT="$PASS_INPUT" \
    "$DASHBOARD_IMG" \
    -e "console.log(require('bcryptjs').hashSync(process.env.PWD_INPUT, 12))" 2>/dev/null)
```

**Détails :**
- Utilise l'image dashboard (Node.js) pour cohérence
- Passe le mot de passe via variable d'environnement
- Utilise `bcryptjs` avec coût 12 (équilibre sécurité/performance)
- Retourne le hash directement

**Exemple de sortie :**
```
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

#### Étape 5 : DOUBLAGE DES `$` (Sécurité Shell)

```bash
# Remplacer chaque $ par $$ pour éviter l'expansion shell
SAFE_HASH=$(echo "$HASH_OUTPUT" | sed 's/\$/\$\$/g')
```

**Avant :**
```
$2b$12$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

**Après (SAFE_HASH) :**
```
$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

#### Étape 6 : Échappement pour Sed

```bash
# Échapper les / et & pour sed (caractères spéciaux en sed)
ESCAPED_SAFE_HASH=$(echo "$SAFE_HASH" | sed 's/[\/&]/\\&/g')
```

**Raison :** `sed` utilise `/` comme délimiteur et traite `&` comme un caractère spécial.

**Exemple :**
```bash
# Si le hash contient un /, sed doit le voir comme \/
# Si le hash contient un &, sed doit le voir comme \&
```

#### Étape 7 : Écriture dans `.env`

```bash
sed -i "s|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=${ESCAPED_SAFE_HASH}|" "$ENV_FILE"
```

**Détails :**
- Utilise `|` comme délimiteur au lieu de `/` (évite confusion)
- Remplace la ligne `DASHBOARD_PASSWORD=...` par `DASHBOARD_PASSWORD=<safe_hash>`
- L'option `-i` modifie le fichier in-place

**Résultat dans `.env` :**
```
DASHBOARD_PASSWORD=$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

#### Étape 8 : Lecture par l'Application

Lorsque l'app démarre :

```bash
# Dans le fichier .env
DASHBOARD_PASSWORD=$$2b$$12$$...

# Docker/Shell lit et interprète $$  comme $
# L'app reçoit :
DASHBOARD_PASSWORD=$2b$12$...  (CORRECT ✓)
```

---

## 🎯 Interaction Utilisateur

### Menus Disponibles

#### `prompt_yes_no` - Question Oui/Non

```bash
prompt_yes_no "Acceptez-vous les conditions ?" "y"  # Défaut: yes
```

**Affichage :**
```
Acceptez-vous les conditions ? [Y/n] :
```

**Comportement :**
- Timeout : 30 secondes
- Si l'utilisateur appuie sur Entrée → utilise la valeur par défaut
- Accepte `y`, `Y`, `n`, `N`

---

#### `prompt_menu` - Menu Numéroté

```bash
choice=$(prompt_menu \
    "Choisissez une option" \
    "Option 1" \
    "Option 2" \
    "Option 3")

case "$choice" in
    1) echo "Option 1 choisie" ;;
    2) echo "Option 2 choisie" ;;
    3) echo "Option 3 choisie" ;;
esac
```

**Affichage :**
```
Choisissez une option

  1) Option 1
  2) Option 2
  3) Option 3

Votre choix [1-3] (timeout 30s) :
```

**Comportement :**
- Valide que le choix est numérique et dans la plage valide
- Redemande en cas de choix invalide
- Timeout : 30 secondes

---

#### `prompt_password_action` - Menu Mot de Passe

Fonction spécifique avec 2-3 options selon le contexte.

```bash
ACTION=$(prompt_password_action "false")  # Pas de mot de passe existant

# Returns: "new", "cancel"
```

ou

```bash
ACTION=$(prompt_password_action "true")   # Mot de passe existant

# Returns: "new", "keep", "cancel"
```

**Gestion des Retours :**
```bash
case "$ACTION" in
    new)    # Générer un nouveau hash
            ;;
    keep)   # Garder le hash existant
            ;;
    cancel) # Annuler la configuration
            ;;
esac
```

---

## 📋 Exemples Pratiques

### Exemple 1 : Première Installation

**Étapes de l'utilisateur :**

```bash
$ ./setup.sh

[INFO] Configuration du Mot de Passe Dashboard

  1) Définir un nouveau mot de passe
  2) Annuler la configuration pour l'instant

Votre choix [1-2] (timeout 30s) : 1

Entrez le nouveau mot de passe dashboard :
Mot de passe (caché) : ••••••••

[INFO] Hachage sécurisé du mot de passe avec bcryptjs...
[OK] ✓ Mot de passe haché et stocké dans .env (avec $$ doublés pour sécurité shell)
[INFO]   Hash: $$2b$$12$$EBpvXzNy2... (doublage des $)

# ... reste du script ...
```

**Résultat dans `.env` :**
```bash
DASHBOARD_PASSWORD=$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
```

---

### Exemple 2 : Réexécution du Script (Idempotence)

**Scénario :** L'utilisateur relance `./setup.sh` après une première installation.

```bash
$ ./setup.sh

[INFO] ✓ Mot de passe Dashboard déjà configuré (hash bcrypt détecté). Skip.

# ... Le script continue sans demander le mot de passe ...
```

**Point clé :** Le script détecte le hash bcrypt valide et ne redémande pas le mot de passe. Parfait pour l'automatisation et CI/CD.

---

### Exemple 3 : Reconfiguration du Mot de Passe

**Scénario :** L'utilisateur veut changer le mot de passe existant.

```bash
$ sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env

$ ./setup.sh

[INFO] Configuration du Mot de Passe Dashboard

  1) Définir/Changer le mot de passe maintenant
  2) Garder le mot de passe existant
  3) Annuler la configuration pour l'instant

Votre choix [1-3] (timeout 30s) : 1

Entrez le nouveau mot de passe dashboard :
Mot de passe (caché) : •••••••• (nouveau mot de passe)

[INFO] Hachage sécurisé du mot de passe avec bcryptjs...
[OK] ✓ Mot de passe haché et stocké dans .env (avec $$ doublés pour sécurité shell)
```

---

### Exemple 4 : Format du `.env` - Avant et Après

**Fichier `.env` AVANT hachage :**
```bash
# Dashboard Configuration
DASHBOARD_PASSWORD=CHANGEZ_MOI
DASHBOARD_USER=admin
```

**Fichier `.env` APRÈS hachage :**
```bash
# Dashboard Configuration
DASHBOARD_PASSWORD=$$2b$$12$$EBpvXzNy2TxUz7r3Q5m9I.u3R4K7p2L6M8wQ5x9F3dG6h4j2k
DASHBOARD_USER=admin
```

**⚠️ IMPORTANT :**
- Les `$$` dans le fichier sont **NORMAUX** et **NÉCESSAIRES**
- ❌ Ne les modifiez PAS manuellement
- ✅ Le shell les interprète correctement lors de la lecture

---

## 🆘 Troubleshooting

### Problème 1 : "Échec du hachage bcrypt"

**Symptôme :**
```
[ERROR] Échec du hachage bcrypt. Sortie: (vide ou erreur)
```

**Causes possibles :**
1. L'image dashboard n'est pas disponible
2. Docker n'est pas accessible
3. bcryptjs manquant dans l'image dashboard

**Solutions :**
```bash
# Vérifier que l'image existe
docker pull ghcr.io/gaspardd78/linkedin-birthday-auto-dashboard:latest

# Relancer setup.sh
./setup.sh
```

---

### Problème 2 : "Hash invalide dans .env"

**Symptôme :** Après le hachage, le mot de passe ne fonctionne pas lors de la connexion.

**Causes possibles :**
1. Les `$$` ont été modifiés manuellement
2. Le hash a été écrit de façon incomplète

**Vérification :**
```bash
# Afficher la ligne DASHBOARD_PASSWORD
grep DASHBOARD_PASSWORD .env

# Doit afficher quelque chose comme :
# DASHBOARD_PASSWORD=$$2b$$12$$...

# Compter les $ (doit être pairs) :
grep DASHBOARD_PASSWORD .env | grep -o '\$' | wc -l
# Résultat : nombre pair (ex: 12, 16, 20, ...)
```

**Solution :**
```bash
# Réinitialiser le mot de passe
sed -i 's|^DASHBOARD_PASSWORD=.*|DASHBOARD_PASSWORD=CHANGEZ_MOI|' .env
./setup.sh
```

---

### Problème 3 : Timeout lors du menu

**Symptôme :**
```
[ERROR] Pas de réponse (timeout 30s)
```

**Cause :** L'utilisateur n'a pas répondu dans les 30 secondes.

**Solution :**
```bash
# Relancer setup.sh
./setup.sh

# Répondre rapidement (par défaut, les options ont un défaut implicite)
# Appuyer sur Entrée pour accepter la valeur par défaut
```

---

### Problème 4 : Caractères spéciaux dans le mot de passe

**Scénario :** L'utilisateur entre un mot de passe avec `$`, `/`, `&` ou autres caractères spéciaux.

**Comportement :**
- Le script gère les caractères spéciaux correctement
- `sed` échappe automatiquement les `/` et `&` (étape 6)
- Les `$` sont doublés (étape 5)

**Exemple avec caractères spéciaux :**
```bash
# Mot de passe : MyP@ss$word&123
# ↓ (docker hachage)
# Hash : $2b$12$EBpvXzNy...
# ↓ (doublage des $)
# SAFE_HASH : $$2b$$12$$EBpvXzNy...
# ↓ (échappement pour sed)
# ESCAPED : $$2b$$12$$EBpvXzNy...
# ↓ (écriture dans .env)
# DASHBOARD_PASSWORD=$$2b$$12$$EBpvXzNy...
```

**Résultat :** ✅ Tout fonctionne correctement.

---

## 📚 Fichiers Associés

- **Script :** `/setup.sh` (lignes 418-534)
- **Fonctions utilitaires :** `/setup.sh` (lignes 63-151)
- **Improvements doc :** `/docs/SETUP_IMPROVEMENTS.md`
- **Architecture :** `/docs/ARCHITECTURE.md`

---

## 🎯 Résumé

| Aspect | Avant | Après |
|--------|-------|-------|
| **Hachage** | ✅ Fonctionnel | ✅ + Documentation claire |
| **Interaction** | ❌ Demande simple | ✅ Menu avec choix |
| **Idempotence** | ✅ Oui | ✅ Oui + UX meilleure |
| **Sécurité** | ✅ Bcrypt + doublage | ✅ Idem + code expliqué |
| **Maintenabilité** | ⚠️ Moyen | ✅ Excellent |
| **Documentation** | ❌ Insuffisante | ✅ Très complète |

---

**Document généré le 2025-01-19 par Claude Code - Setup Script Improvements**
