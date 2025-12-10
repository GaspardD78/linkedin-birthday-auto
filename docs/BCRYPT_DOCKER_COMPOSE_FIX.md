# Fix: Bcrypt Hash dans Docker Compose

## 🐛 Problème

Lors de l'exécution de `setup_security.sh`, vous pouvez rencontrer des warnings Docker Compose du type :

```
WARN[0000] The "b7nXQ1DZRVyElLu0mQGscuDOdLrUZK4eu" variable is not set. Defaulting to a blank string.
```

### Cause

Les hashs bcrypt contiennent des caractères `$` (par exemple : `$2a$12$abc123...`). Docker Compose interprète ces `$` comme des **marqueurs de substitution de variables d'environnement**.

**Exemple :**
```bash
# Dans .env
DASHBOARD_PASSWORD=$2a$12$b7nXQ1DZRVyElLu0mQGscuDOdLrUZK4eu...

# Docker Compose interprète :
# - $2a → variable "2a" (vide)
# - $12 → variable "12" (vide)
# - $b7nXQ... → variable "b7nXQ1DZRVyElLu0mQGscuDOdLrUZK4eu" (vide)
```

Résultat : Le mot de passe devient une chaîne vide, et vous ne pouvez pas vous connecter au dashboard.

---

## ✅ Solution

### Option 1 : Script de correction automatique (Recommandé)

Si vous avez déjà un fichier `.env` avec un hash bcrypt non protégé :

```bash
./scripts/fix_env_password.sh
```

Ce script :
1. ✅ Détecte automatiquement le hash bcrypt dans `.env`
2. ✅ Ajoute des quotes simples autour du hash
3. ✅ Crée un backup avant modification
4. ✅ Affiche les instructions pour redémarrer

### Option 2 : Correction manuelle

1. **Ouvrez le fichier `.env` :**
   ```bash
   nano .env
   ```

2. **Trouvez la ligne `DASHBOARD_PASSWORD` :**
   ```bash
   # ❌ AVANT (incorrect)
   DASHBOARD_PASSWORD=$2a$12$b7nXQ1DZRVyElLu0mQGscuDOdLrUZK4eu...
   ```

3. **Ajoutez des quotes simples autour du hash :**
   ```bash
   # ✅ APRÈS (correct)
   DASHBOARD_PASSWORD='$2a$12$b7nXQ1DZRVyElLu0mQGscuDOdLrUZK4eu...'
   ```

4. **Sauvegardez et quittez** (Ctrl+O, Enter, Ctrl+X)

5. **Redémarrez le dashboard :**
   ```bash
   docker compose restart dashboard
   ```

---

## 🔍 Vérification

### Vérifier que le problème est résolu

```bash
# 1. Vérifier qu'il n'y a plus de warnings
docker compose config | grep -i warn

# 2. Vérifier que la variable est correctement lue
docker compose config | grep DASHBOARD_PASSWORD

# 3. Voir les logs du dashboard
docker compose logs dashboard
```

### Résultat attendu

- ✅ Aucun warning Docker Compose
- ✅ Le hash bcrypt est correctement lu comme une chaîne
- ✅ Vous pouvez vous connecter au dashboard avec votre mot de passe

---

## 📚 Explication technique

### Pourquoi les quotes simples ?

Docker Compose supporte plusieurs formats pour les valeurs dans `.env` :

| Format | Interprétation | Résultat avec bcrypt |
|--------|----------------|----------------------|
| `VAR=$2a$12$abc` | ❌ Substitution de variables | Hash cassé |
| `VAR="$2a$12$abc"` | ❌ Substitution même entre doubles quotes | Hash cassé |
| `VAR='$2a$12$abc'` | ✅ Littéral (pas de substitution) | ✅ Hash intact |

**Règle :** Les quotes simples `'...'` désactivent **toutes** les substitutions.

### Références

- [Docker Compose - Environment Variables](https://docs.docker.com/compose/environment-variables/)
- [Docker Compose - Variable Substitution](https://docs.docker.com/compose/compose-file/12-interpolation/)

---

## 🔧 Correction préventive

Le script `setup_security.sh` a été mis à jour pour :

1. **Automatiquement** ajouter les quotes simples lors de la génération du hash
2. **Détecter** si le hash est déjà protégé
3. **Afficher** un message d'erreur si `.env` n'existe pas

Si vous réexécutez `setup_security.sh`, le hash sera correctement formaté.

---

## 🆘 Problèmes persistants

### Erreur : "Invalid credentials" après la correction

**Cause possible :** Le hash bcrypt a été corrompu lors de la manipulation.

**Solution :**
```bash
# Régénérer un nouveau hash
cd dashboard
npm install bcryptjs
node scripts/hash_password.js "VotreMotDePasse"

# Copier le hash généré et le mettre dans .env avec quotes simples
nano ../.env
# DASHBOARD_PASSWORD='$2a$12$nouveauHash...'
```

### Warning persiste après redémarrage

**Vérification :**
```bash
# Afficher la ligne exacte dans .env
grep "^DASHBOARD_PASSWORD" .env

# Doit afficher :
# DASHBOARD_PASSWORD='$2a$12$...'
#                    ↑        ↑
#                    quotes présentes
```

Si les quotes ne sont pas présentes, relancez `./scripts/fix_env_password.sh`.

---

## 📝 Notes supplémentaires

### Autres variables affectées

Ce problème peut aussi affecter d'autres variables contenant des `$` :
- `JWT_SECRET` (si contient des $)
- `API_KEY` (si contient des $)
- Mots de passe SMTP (si contiennent des $)

**Recommandation :** Utilisez toujours des quotes simples pour les valeurs sensibles dans `.env`.

### Compatibilité

Cette solution fonctionne avec :
- ✅ Docker Compose v2.x
- ✅ Docker Compose v1.x
- ✅ docker-compose (ancien binaire)

---

## 🎯 Résumé

| Problème | Solution |
|----------|----------|
| Docker Compose interprète `$` dans hash bcrypt | Entourer le hash de quotes simples `'...'` |
| Script automatique | `./scripts/fix_env_password.sh` |
| Correction manuelle | Éditer `.env` et ajouter `'...'` |
| Prévention | `setup_security.sh` a été corrigé |

---

**Version :** 1.0
**Date :** 2025-12-10
**Auteur :** Claude Code
