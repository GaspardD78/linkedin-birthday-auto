# 🚨 QUICK FIX : Impossible de se connecter au Dashboard

## Le problème

Vous ne pouvez pas vous connecter au dashboard même avec les bons identifiants.
**Cause** : Le hash bcrypt dans votre `.env` local utilise `$` au lieu de `$$`, ce qui pose problème avec Docker Compose.

---

## ✅ Solution rapide (2 minutes)

### Sur votre Raspberry Pi, exécutez :

```bash
cd ~/linkedin-birthday-auto

# Étape 1 : Lancer le script de correction automatique
./scripts/fix_env_password.sh
```

Le script va :
1. Vous demander un nouveau mot de passe
2. Générer le hash bcrypt correct (avec `$$`)
3. Mettre à jour votre `.env` local
4. Redémarrer le dashboard

**C'est tout !** ✨

---

## 🔍 Alternative : Diagnostic d'abord

Si vous voulez d'abord comprendre le problème :

```bash
# Voir ce que contient le container dashboard
./scripts/test_dashboard_env.sh
```

Ce script vous montrera exactement ce que voit le container et vous dira quoi corriger.

---

## 🛠️ Solution manuelle (si les scripts ne fonctionnent pas)

### Étape 1 : Générer un nouveau hash

```bash
cd ~/linkedin-birthday-auto
node dashboard/scripts/hash_password.js "VotreMotDePasse"
```

Vous verrez quelque chose comme :
```
✅ Mot de passe hashé avec succès!

Copiez cette ligne dans votre fichier .env:
─────────────────────────────────────────────────
DASHBOARD_PASSWORD=$$2a$$12$$AbCdEf...
─────────────────────────────────────────────────
```

**IMPORTANT** : Notez les `$$` (double dollar) - c'est normal et nécessaire !

### Étape 2 : Modifier votre .env local

```bash
nano .env
```

Trouvez la ligne `DASHBOARD_PASSWORD=...` et remplacez-la par le hash généré.

**Vérifiez bien** :
- ✅ Le hash doit commencer par `$$2a$$12$$` (avec des doubles `$$`)
- ❌ PAS `$2a$12$` (dollar simple = ne fonctionnera pas)

### Étape 3 : Sauvegarder et quitter

- Appuyez sur `Ctrl + O` pour sauvegarder
- Appuyez sur `Entrée` pour confirmer
- Appuyez sur `Ctrl + X` pour quitter

### Étape 4 : Redémarrer le dashboard

```bash
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

### Étape 5 : Vérifier les logs

```bash
docker compose -f docker-compose.pi4-standalone.yml logs -f dashboard
```

Attendez de voir `✓ Ready` ou similaire.

### Étape 6 : Se connecter

Allez sur `http://IP_RASPBERRY:3000` et connectez-vous avec :
- **Utilisateur** : `admin` (ou ce que vous avez défini dans `DASHBOARD_USER`)
- **Mot de passe** : Le mot de passe **en clair** que vous avez utilisé à l'étape 1 (PAS le hash)

---

## 🎯 Exemple concret

Imaginons que vous voulez le mot de passe `MonSuperMotDePasse123!`

### 1. Générer le hash

```bash
node dashboard/scripts/hash_password.js "MonSuperMotDePasse123!"
```

Résultat :
```
DASHBOARD_PASSWORD=$$2a$$12$$xyz123abc...
```

### 2. Mettre dans .env

```bash
nano .env
```

Modifier la ligne :
```
DASHBOARD_PASSWORD=$$2a$$12$$xyz123abc...
```

### 3. Redémarrer

```bash
docker compose -f docker-compose.pi4-standalone.yml restart dashboard
```

### 4. Se connecter

- Utilisateur : `admin`
- Mot de passe : `MonSuperMotDePasse123!` (le mot de passe en clair, pas le hash !)

---

## ❓ Pourquoi les `$$` ?

Docker Compose interprète les `$` dans les fichiers `.env` comme des variables d'environnement.

**Exemple** :
- Hash original bcrypt : `$2a$12$abc...`
- Docker Compose voit : `{variable vide}2a{variable vide}12{variable vide}abc...`
- Résultat : `2a12abc...` (hash cassé !)

**Solution** : Doubler les `$` pour que Docker Compose comprenne que c'est littéral :
- Hash dans .env : `$$2a$$12$$abc...`
- Docker Compose voit : `$2a$12$abc...` (correct !)

Le script `hash_password.js` fait ça automatiquement maintenant.

---

## 🆘 Toujours pas de connexion ?

### Vérification 1 : Le container voit-il le bon hash ?

```bash
docker exec dashboard env | grep DASHBOARD_PASSWORD
```

Vous devriez voir : `DASHBOARD_PASSWORD=$2a$12$...` (avec des `$` simples - c'est normal DANS le container)

Si vous voyez une chaîne vide ou bizarre, le .env n'a pas été chargé → Redémarrez le dashboard.

### Vérification 2 : Logs d'erreur ?

```bash
docker logs dashboard --tail 50
```

Recherchez des erreurs liées à `auth`, `login`, `JWT`, `bcrypt`.

### Vérification 3 : Variables d'environnement complètes ?

```bash
docker exec dashboard env | grep -E "(DASHBOARD_USER|DASHBOARD_PASSWORD|JWT_SECRET)"
```

Les 3 doivent être définies et non vides.

### Vérification 4 : Test de mot de passe simple

Créez un mot de passe de test très simple :

```bash
node dashboard/scripts/hash_password.js "test1234"
```

Mettez ce hash dans `.env`, redémarrez, et testez avec `test1234`.

Si ça fonctionne → Le problème était votre ancien mot de passe ou hash.
Si ça ne fonctionne pas → Problème plus profond (vérifiez les logs).

---

## 📞 Besoin d'aide ?

Exécutez ces commandes et partagez les résultats :

```bash
# Configuration du .env
./scripts/test_dashboard_env.sh

# Logs récents
docker logs dashboard --tail 30

# État des containers
docker compose -f docker-compose.pi4-standalone.yml ps
```

---

## ✅ Checklist de vérification

Avant de demander de l'aide, vérifiez que vous avez bien :

- [ ] Exécuté `./scripts/fix_env_password.sh` OU régénéré le hash manuellement
- [ ] Le hash dans `.env` commence bien par `$$2a$$12$$` (double `$$`)
- [ ] Redémarré le dashboard après modification du `.env`
- [ ] Utilisé le mot de passe **en clair** pour vous connecter (pas le hash)
- [ ] Le container dashboard est bien démarré (`docker ps | grep dashboard`)
- [ ] Vérifié les logs (`docker logs dashboard`)

---

**Dernière mise à jour** : 2025-12-10
